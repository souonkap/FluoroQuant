#!/opt/miniconda3/envs/tbtkr/bin/python3
#-*- coding: utf-8 -*-

import wx
import wx.adv
import cv2 as cv
import io
import numpy as np
from glob import glob
from os.path import join
import os
from pathlib import Path
import csv
import tempfile
from random import randint
import math
import pandas as pd
import statistics as stat
tempdir = tempfile.TemporaryDirectory()
temp_dir = tempdir.name
title = 'StaticTracker'

class Screen(wx.Panel):
	def __init__(self, parent, path, size = (1000, 800), pos = (222, 20)):
		self.size = Point(x = size[0], y = size[1])
		wx.Panel.__init__(self, parent, size = self.size.coor, pos = pos)
		self.parent = parent
		self.points_to_add = []
		self.path = path
		self.ratios = (1, 1)
		cv.imwrite(self.path + "/logo.png", cv.resize(cv.imread("logo.png"), self.size.coor))
		self.imageCtrl = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(wx.Image(self.path + "/logo.png", wx.BITMAP_TYPE_ANY)))
		self.Layout()

	def display(self, img):
		img_path = self.path + "/img.png"
		cv.imwrite(img_path, cv.resize(img, self.size.coor))
		self.imageCtrl.SetBitmap(wx.Bitmap(wx.Image(img_path, wx.BITMAP_TYPE_ANY)))
		self.Refresh()

class Point:
	def __init__(self, x = 0, y = 0):
		self.x = x
		self.y = y
		self.coor = (x, y)

class ROI:
	def __init__(self, center, frame, ID, roi_len, trk_id = None):
		self.center = center
		self.trk_id = trk_id
		self.ID = ID
		self.frame = frame
		self.roi_len = roi_len
		self.top_left = Point(x = center.x - int(roi_len/2), y = center.y - int(roi_len/2))
		self.bot_right = Point(x = center.x + int(roi_len/2), y = center.y + int(roi_len/2))

class S_Tracker(wx.Panel):
	def __init__(self, parent, path, screen_size = (1000, 800), screen_pos = (222, 20)):
		wx.Panel.__init__(self, parent, size = screen_size, pos = screen_pos)
		self.parent = parent
		self.Bind(wx.EVT_MOTION, self.on_mouse_move)
		self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_click)
		self.Bind(wx.EVT_RIGHT_DOWN, self.on_mouse_click)
		self.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
		self.fixed_length = False
		self.add_xtra_roi = False
		self.roi_len = 24
		self.trk_len = 24
		self.ds = 4
		self.set_defaults()
		self.Layout()

	def on_mouse_click(self, e):
		pos = self.ScreenToClient(e.GetPosition())
		screen_pos = self.GetScreenPosition()
		c1 = Point(x = int((pos[0] + screen_pos[0])), y = int((pos[1] + screen_pos[1])))
		if self.cur_trk.roi_num == 0:
			self.c1 = c1
			self.cur_trk.add_roi(point = c1, roi_len = self.roi_len, frame = self.frame)
		else:
			if self.fixed_length == False:
				self.c1 = c1
			else:
				if (self.cur_trk.sequence[-1].center.x - c1.x) != 0: 
					rot_angle = math.atan((c1.y - self.cur_trk.sequence[-1].center.y)/(c1.x - self.cur_trk.sequence[-1].center.x))
					if self.cur_trk.sequence[-1].center.x >= c1.x:
						dx = self.trk_len*math.cos(rot_angle)
						if self.cur_trk.sequence[-1].center.y <= c1.y:
							dy = -1*self.trk_len*math.sin(rot_angle)
						else:
							dy = self.trk_len*math.sin(rot_angle)
					else:
						dx = -1*self.trk_len*math.cos(rot_angle)
						if self.cur_trk.sequence[-1].center.y <= c1.y:
							dy = self.trk_len*math.sin(rot_angle)
						else:
							dy = -1*self.trk_len*math.sin(rot_angle)
					if self.cur_trk.sequence[-1].center.y < c1.y:
						dy = -dy
					self.c1 = Point(x = self.cur_trk.sequence[-1].center.x-dx, y = self.cur_trk.sequence[-1].center.y-dy)
				else:
					if self.cur_trk.sequence[-1].center.y <= c1.y:
						self.c1 = Point(x = self.cur_trk.sequence[-1].center.x, y = self.cur_trk.sequence[-1].center.y-dy)
					else:
						self.c1 = Point(x = self.cur_trk.sequence[-1].center.x, y = self.cur_trk.sequence[-1].center.y+dy)
			if self.add_xtra_roi == True:
				ds = self.ds
			else:
				ds = 1
			self.cur_trk.add_roi(ds = ds, point = self.c1, roi_len = self.roi_len, frame = self.frame)
		self.Refresh()

	def on_mouse_move(self, e):
		self.c2 = e.GetPosition()
		self.Refresh()
		#if event.Dragging() and event.LeftIsDown():
		#	self.c2 = event.GetPosition()
		#	self.Refresh()

	def on_mouse_up(self, e):
		self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

	def on_paint(self, e):
		dc = wx.PaintDC(self)
		dc.SetPen(wx.Pen('gray', 1))
		dc.SetBrush(wx.Brush("BLACK", wx.TRANSPARENT))
		dc.DrawLine(0, self.c2.y,18000, self.c2.y)
		dc.DrawLine(self.c2.x, 0, self.c2.x, 18000)
		if self.c1 != None:
			dc.DrawLine(self.c1.x, self.c1.y, self.c2.x, self.c2.y)
		if self.cur_trk.roi_num > 0:
			for roi in self.cur_trk.sequence:
				if roi.frame == self.frame:
					dc.DrawRectangle(roi.top_left.x, roi.top_left.y, int(roi.roi_len), int(roi.roi_len))
			if self.cur_trk.roi_num > 1:
				for i in range(1, self.cur_trk.roi_num):
					if self.cur_trk.sequence[i-1].frame == self.cur_trk.sequence[i].frame == self.frame:
						dc.DrawLine(self.cur_trk.sequence[i-1].center.x, self.cur_trk.sequence[i-1].center.y, self.cur_trk.sequence[i].center.x, self.cur_trk.sequence[i].center.y)
		if len(self.valid_trks) > 0:
			for trk in self.valid_trks:
				if trk.roi_num > 0:
					for roi in trk.sequence:
						if roi.frame == self.frame:
							dc.DrawRectangle(roi.top_left.x, roi.top_left.y, int(roi.roi_len), int(roi.roi_len))
					if trk.roi_num > 1:
						for i in range(1, trk.roi_num):
							if trk.sequence[i-1].frame == trk.sequence[i].frame == self.frame:
								dc.DrawLine(trk.sequence[i-1].center.x, trk.sequence[i-1].center.y, trk.sequence[i].center.x, trk.sequence[i].center.y)

	def set_defaults(self):
		self.c1 = None
		self.c2 = Point(x = 0, y = 0)
		self.valid_trks = []
		self.frame = 0
		self.trk_id = 1
		self.cur_trk = Track(self.trk_id)
		self.Refresh()

	def validate_cur_trk(self):
		if self.cur_trk.roi_num > 0:
			self.valid_trks.append(self.cur_trk)
			self.trk_id += 1
		self.cur_trk = Track(self.trk_id)
		self.c1 = None

class Track:
	def __init__(self, ID, rois = []):
		self.sequence = []
		self.ID = ID
		self.length = 0
		self.leng = 0
		self.roi_num = 0
		if len(rois) > 0:
			self.add_rois(rois)

	def add_roi_ori(self, point, roi_len, frame, ds = 1):
		if self.roi_num == 0:
			self.roi_num +=1
			self.sequence.append(ROI(center = point, frame = frame, trk_id = self.ID, ID = self.roi_num, roi_len = roi_len))
		else:
			dy = (point.y - self.sequence[-1].center.y)/ds
			if abs(dy) < 1:
				if dy < 0:
					dy = -1
				elif dy > 0:
					dy = 1
			dx = (point.x - self.sequence[-1].center.x)/ds
			if abs(dx) < 1:
				if dx < 0:
					dx = -1
				elif dx > 0:
					dx = 1
			i = 0
			while(True):
				i += 1
				if i > ds:
					break
				pt = Point(x = int(self.sequence[-1].center.x + dx), y = int(self.sequence[-1].center.y + dy))
				self.roi_num +=1
				self.sequence.append(ROI(center = pt, frame = frame, trk_id = self.ID, ID = self.roi_num, roi_len = roi_len))

	def add_roi(self, box):
		if self.leng == 0:
			self.sequence.append(box)
			self.leng += 1
		elif box.frame < self.sequence[0].frame:
			self.sequence.insert(0,box)
			self.leng += 1
		elif box.frame > self.sequence[-1].frame:
			self.sequence.append(box)
			self.leng += 1
		else:
			for i in range(1, self.leng):
				if self.sequence[i-1].frame < box.frame < self.sequence[i].frame:
					self.sequence.insert(i, box)
					self.leng += 1
					break

	def add_rois(self, boxes):
		for box in boxes:
			self.add_roi(box)

	def get_info(self, img_list, img_ratios, min_int, img_paths, img_foregrounds, img_backgrounds, img_means):
		out = []
		if self.roi_num > 0:
			l = 0
			p_center = None 
			delim = ", "
			rd = 4
			for roi in self.sequence:
				img = cv.cvtColor(img_list[roi.frame], cv.COLOR_BGR2GRAY)
				h, w = img.shape
				ratio = img_ratios[roi.frame]
				if roi.top_left.x < 0:
					lx = 0
				else:
					lx = int(roi.top_left.x*ratio.x)
				if roi.top_left.y < 0:
					ty = 0
				else:
					ty = int(roi.top_left.y*ratio.y)
				if int(roi.bot_right.x*ratio.x) < w:
					rx = int(roi.bot_right.x*ratio.x)
				else:
					rx = w - 1 
				if int(roi.bot_right.y*ratio.y) < h:
					by = int(roi.bot_right.y*ratio.y)
				else:
					by = h - 1
				crop = img[ty:by, lx:rx]
				all_pxl = []
				for j in range(256):
					all_pxl.append(np.sum(crop == j)) 
				center = Point(x = int(roi.center.x*ratio.x), y = int(roi.center.y*ratio.y))
				if p_center != None:
					l +=  pow(pow((center.y - p_center.y), 2) + pow((center.x - p_center.x), 2), 0.5)
				p_center = Point(x = int(roi.center.x*ratio.x), y = int(roi.center.y*ratio.y))
				out.append([img_paths[roi.frame], roi.ID, center.x, center.y, abs((by-ty+1)*(rx-lx+1)), np.sum(crop >= min_int), delim.join(map(str, all_pxl)), round(l, rd), round(np.mean(crop[crop >= min_int]), rd), round(img_foregrounds[roi.frame], rd), round(img_backgrounds[roi.frame], rd), round(img_means[roi.frame], rd)])
		return out

class ST_GUI(wx.Frame):
	def __init__(self, title = title):
		wx.Frame.__init__(self, None, title = title)
		self.user_sreen_size = wx.GetDisplaySize()
		self.SetBackgroundColour(self.next_color("warm"))
		panel = wx.Panel(self)
		wx.StaticBox(panel, label = 'Image Parameters', pos = self.position_of("ly_image_params"), size = self.size_of("ly_image_params"))
		wx.StaticBox(panel, label = 'Display', pos = self.position_of("ly_display"), size = self.size_of("ly_display"))
		self.screen = Screen(panel,temp_dir, size = self.size_of("screen"), pos = self.position_of("screen"))
		self.tracker = S_Tracker(panel,temp_dir, screen_size = self.size_of("screen"), screen_pos = self.position_of("screen"))
		input_dir = wx.Button(panel, label = "Images Location", size = self.size_of("btn_input_dir"), pos = self.position_of("btn_input_dir"))
		input_dir.Bind(wx.EVT_BUTTON, self.on_input_dir)
		self.ext_cb = wx.ComboBox(panel, choices = ['.avi', '.png', '.tiff', '.tif', '.jpeg', '.jpg', '.gif'], size = self.size_of("cb_ext"), pos = self.position_of("cb_ext"))
		self.ext_cb.Bind(wx.EVT_COMBOBOX, self.on_ext_cb)
		self.cb_id = 0
		labels = [["fixed_step", self.position_of("cb_fixed_length")], ["extra_ROI", self.position_of("cb_xtra_roi")]]
		for label in labels:
			self.make_checkboxes(panel, label[0], label[1], self.on_checkboxes, self.cb_id)
			self.cb_id += 1
		self.cb_fixed_length = self.FindWindowByLabel("fixed_step")
		self.cb_extra_roi = self.FindWindowByLabel("extra_ROI")
		wx.StaticText(panel, label = "ROI_side", style = wx.ALIGN_LEFT, pos = self.position_of("st_roi"))
		self.fixed_roi_len = wx.TextCtrl(panel, value = str(self.tracker.roi_len), size = self.size_of("tc_fixed_roi_len"), pos = self.position_of("tc_fixed_roi_len"))
		self.fixed_roi_len.Bind(wx.EVT_TEXT, self.on_fixed_roi_len)
		wx.StaticText(panel, label = "pixels", style = wx.ALIGN_LEFT, pos = self.position_of("st_pixel_1"))
		self.fixed_trk_len = wx.TextCtrl(panel, value = str(self.tracker.trk_len), size = self.size_of("tc_fixed_trk_len"), pos = self.position_of("tc_fixed_trk_len"))
		self.fixed_trk_len.Bind(wx.EVT_TEXT, self.on_fixed_trk_len)
		wx.StaticText(panel, label = "pixels", style = wx.ALIGN_LEFT, pos = self.position_of("st_pixel_2"))
		self.fixed_dx = wx.TextCtrl(panel, value = str(self.tracker.ds), size = self.size_of("tc_fixed_dx"), pos = self.position_of("tc_fixed_dx"))
		self.fixed_dx.Bind(wx.EVT_TEXT, self.on_xtra_roi)
		validate = wx.Button(panel, label = "Validate", size = self.size_of("btn_validate"), pos = self.position_of("btn_validate"))
		validate.Bind(wx.EVT_BUTTON, self.on_validate)
		remove = wx.Button(panel, label = "Remove", size = self.size_of("btn_remove"), pos = self.position_of("btn_remove"))
		remove.Bind(wx.EVT_BUTTON, self.on_remove)
		wx.StaticText(panel, label = "min_intensity", style = wx.ALIGN_LEFT, pos = self.position_of("st_min_intensity"))
		self.min_pxl_int = 10
		self.min_pxl_tc = wx.TextCtrl(panel, value = str(self.min_pxl_int), size = self.size_of("tc_min_pxl"), pos = self.position_of("tc_min_pxl"))
		self.min_pxl_tc.Bind(wx.EVT_TEXT, self.on_min_pxl)
		self.save_name = wx.TextCtrl(panel, value = "    Please enter save name", size = self.size_of("tc_save_name"), pos = self.position_of("tc_save_name"))
		self.save_name.Bind(wx.EVT_TEXT, self.on_save_name)
		save = wx.Button(panel, label = "Save", size = self.size_of("btn_save"), pos = self.position_of("btn_save"))
		save.Bind(wx.EVT_BUTTON, self.on_save)
		reverse_button = wx.Button(panel, label = "<<", size = self.size_of("btn_reverse"), pos = self.position_of("btn_reverse"))
		reverse_button.Bind(wx.EVT_BUTTON, self.on_reverse)
		forward_button = wx.Button(panel, label = ">>", size = self.size_of("btn_forward"), pos = self.position_of("btn_forward"))
		forward_button.Bind(wx.EVT_BUTTON, self.on_forward)
		self.frame_display = wx.StaticText(panel, label = "1", style = wx.ALIGN_LEFT, pos = self.position_of("st_frame_display"))
		wx.StaticText(panel, label = "Image:", style=wx.ALIGN_LEFT, pos = self.position_of("st_image_number"))
		self.ext = '.avi'
		self.savename = "output"
		self.valid_roi = []
		self.trk_id = 0
		self.img_num = 1
		self.Maximize(True)

	def get_file_names(self, paths):
		out = []
		for p in paths:
			if p.find('/') >= 0:#Mac OS or Linux
				sep = "/"
			elif p.find("\\\\") >= 0:#windows
				sep = "\\\\"
			elif p.find("\\") >= 0:#windows
				sep = "\\"
			else:
				sep =  None
			if sep == None:
				out.append(p)
			else:
				c = ""
				i = 0
				while(True):
					i -=1
					if p[i] == sep:
						out.append(c)
						break
					c = p[i] + c
		return out

	def make_checkboxes(self, panel, label, pos, bind, id):
		cb = wx.CheckBox(panel, id, label = label, pos = pos)
		self.Bind(wx.EVT_CHECKBOX, bind, cb)

	def next_color(self, genre = None):
		if genre == None:
			return (randint(0, 256),randint(0, 256),randint(0, 256))
		else:
			return (randint(100, 240),randint(100, 240),randint(100, 240))

	def on_checkboxes(self, e):
		if self.cb_fixed_length.GetValue() == True:
			self.tracker.fixed_length = True
			self.tracker.Refresh()
		elif self.cb_fixed_length.GetValue() == False:
			self.tracker.fixed_length = False
			self.tracker.Refresh()
		if self.cb_extra_roi.GetValue() == True:
			self.tracker.add_xtra_roi = True
			self.tracker.Refresh()
		elif self.cb_extra_roi.GetValue() == False:
			self.tracker.add_xtra_roi = False

	def on_ext_cb(self, e):
		self.ext = self.ext_cb.GetValue()

	def on_fixed_roi_len(self, e):
		self.tracker.roi_len = int(self.fixed_roi_len.GetValue())
		self.tracker.Refresh()

	def on_fixed_trk_len(self, e):
		self.tracker.trk_len = int(self.fixed_trk_len.GetValue())
		self.tracker.Refresh()

	def on_forward(self, e):
		if len(self.images) > 1:
			self.tracker.frame += 1
			if self.tracker.frame >= len(self.images):
				self.tracker.frame = 0
			self.screen.display(self.images[self.tracker.frame])
			self.frame_display.SetLabel(str(self.tracker.frame + 1))
			self.tracker.Refresh()

	def on_input_dir_ori(self, e):
		dlg = wx.DirDialog(self, "Choose sample Directory:", style = wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST|wx.DD_CHANGE_DIR)
		if dlg.ShowModal() == wx.ID_OK:
			data_dir = dlg.GetPath()
			self.input_paths = sorted(glob(data_dir + '/*' + self.ext))
			self.savename = self.get_file_names([data_dir])[0]
			self.file_names = self.get_file_names(self.input_paths)
			self.images = []
			self.img_ratios = []
			for img_path in self.input_paths:
				img = cv.imread(img_path)
				h,w,l = img.shape
				self.img_ratios.append(Point(x = w/self.screen.size.x, y = h/self.screen.size.y))
				self.images.append(img)
			self.tracker.set_defaults()
			self.img_num = len(self.images)
			self.screen.display(self.images[self.tracker.frame])
			self.frame_display.SetLabel(str(self.tracker.frame + 1))
			self.tracker.Refresh()
		dlg.Destroy()

	def on_input_dir(self, e):
		dlg = wx.DirDialog(self, "Choose sample Directory:", style = wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST|wx.DD_CHANGE_DIR)
		if dlg.ShowModal() == wx.ID_OK:
			data_dir = dlg.GetPath()
			self.input_paths = sorted(glob(data_dir + '/*' + self.ext))
			#self.track = sorted(glob(data_dir + '/*.csv'))#######
			#self.savename = self.get_file_names([data_dir])[0]
			#self.file_names = self.get_file_names(self.input_paths)
			#self.images = []
			#self.img_ratios = []
			dx = 16
			lwd = 1
			lwd2 = 1
			for img_path in self.input_paths:
				print(img_path)
				tracks = []
				df = pd.read_csv(img_path + '.csv', names=['trk_id', 'frame', 'x', 'y'])
				for trk in range(df.trk_id.max() + 1):
					#track = Track(ID = 0)
					rois = []
					for _, row in df[df.trk_id == trk].iterrows():
						rois.append(ROI(center = Point(x = row.x, y = row.y), frame = row.frame, roi_len = dx, ID = 0))
					if len(rois) > 0:
						tracks.append(Track(ID = 0, rois = rois))
				cap = cv.VideoCapture(img_path)
				mv = []
				fr = -1
				while(True):
					fr += 1
					ret, img = cap.read()
					if ret == False:
						break
					h, w, l = img.shape
					l = 0.905
					l2 = 0.85
					img = cv.resize(img, (int(l*w), int(l2*h)))#############
					for t in tracks:
						for r in t.sequence:
							if r.frame == fr:
								cv.rectangle(img, r.top_left.coor, r.bot_right.coor, (255,0,255), lwd)
						if t.leng > 2:
							if t.sequence[1].frame <= fr:
								for k in range(1, t.leng -1):
									if t.sequence[k].frame <= fr:
										cv.line(img, t.sequence[k-1].center.coor, t.sequence[k].center.coor, (255,0,255), lwd2)
					mv.append(img)
				self.f17(filename = img_path + '.all.avi', img_list = mv)


				#img = cv.imread(img_path)
				#h,w,l = img.shape
				#self.img_ratios.append(Point(x = w/self.screen.size.x, y = h/self.screen.size.y))
				#self.images.append(img)
			#self.tracker.set_defaults()
			#self.img_num = len(self.images)
			#self.screen.display(self.images[self.tracker.frame])
			#self.frame_display.SetLabel(str(self.tracker.frame + 1))
			#self.tracker.Refresh()
		dlg.Destroy()

	def f17(self, filename, img_list, img_per_sec = 25):
		try:
			h, w, l = img_list[0].shape
		except:
			h, w = img_list[0].shape
		writer = cv.VideoWriter(filename, cv.VideoWriter_fourcc(*'MJPG'), img_per_sec, (w, h))
		for img in img_list:
			writer.write(img)
		writer.release()
		writer = None

	def on_min_pxl(self, e):
		self.min_pxl_int = int(self.min_pxl_tc.GetValue())

	def on_remove(self, e):
		self.tracker.c1 = None
		self.tracker.cur_trk = Track(0)
		self.tracker.Refresh()

	def on_reverse(self,e):
		if len(self.images) > 1:
			self.tracker.frame -= 1
			if self.tracker.frame < 0:
				self.tracker.frame = len(self.images) - 1
			self.screen.display(self.images[self.tracker.frame])
			self.frame_display.SetLabel(str(self.tracker.frame + 1))
			self.tracker.Refresh()

	def on_save(self, e):
		dlg = wx.DirDialog(self, "Choose Output Directory:", style = wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST|wx.DD_CHANGE_DIR)
		if dlg.ShowModal() == wx.ID_OK:
			data_dir = dlg.GetPath()
			name = data_dir + "/" + self.savename + ".csv"
			if len(self.tracker.valid_trks) > 0:
				mean_img_pxl = []
				mean_img_bg = []
				mean_img_fg = []
				for img in self.images:
					imgray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
					if imgray.max() >= self.min_pxl_int:
						mean_img_fg.append(np.mean(imgray[imgray >= self.min_pxl_int]))
					else:
						mean_img_fg.append(0)
					if self.min_pxl_int > 1:
						mean_img_bg.append(np.mean(imgray[imgray < self.min_pxl_int]))
					else:
						mean_img_fg.append(0)
					mean_img_pxl.append(np.mean(imgray))
				with open(name, 'w', newline='') as f:
					writer = csv.writer(f)
					writer.writerow(["file", "track_id", "roi_id", "center_x", "center_y", "total_pixel_number", "positive_pixel_number", "ordered_pixel_gray_values_freq (total_count)", "distance_from_roi_1", "mean_pixel_gray_value", "file_mean_foregroud_pixel_value", "file_mean_background_pixel_value", "file_mean_pixel_value"])
					k = 0
					for track in self.tracker.valid_trks:
						if track.roi_num > 0:
							k +=1
							rows = track.get_info(img_list = self.images, img_ratios = self.img_ratios, min_int = self.min_pxl_int, img_paths = self.file_names, img_foregrounds = mean_img_fg, img_backgrounds = mean_img_bg, img_means = mean_img_pxl)
							for row in rows:
								row.insert(1, k)
								writer.writerow(row)

	def on_save_name(self, e):
		self.savename = self.save_name.GetValue()

	def on_validate(self, e):
		self.tracker.validate_cur_trk()
		self.tracker.Refresh()

	def on_xtra_roi(self, e):
		self.tracker.ds = int(self.fixed_dx.GetValue())
		if self.tracker.ds < 1:
			self.tracker.ds = 1

	def position_of(self, item):
		p = 50
		if item == "ly_image_params":
			xy = (5, 0)
		elif item == "ly_display":
			xy = (215, 0)
		elif item == "screen":
			xy = (222,20)
		elif item == "btn_input_dir":
			xy = (15, p)
		elif item == "cb_ext":
			xy = (150, p)
		elif item == "cb_fixed_length":
			xy = (15, 2*p)
		elif item == "tc_fixed_trk_len":
			xy = (110, 2*p)
		elif item == "st_pixel_2":
			xy = (160, 2*p)
		elif item == "st_roi":
			xy = (35, 3*p)
		elif item == "tc_fixed_roi_len":
			xy = (110, 3*p)
		elif item == "st_pixel_1":
			xy = (160, 3*p)
		elif item == "st_xtra_roi":
			xy = (35, 4*p)
		elif item == "cb_xtra_roi":
			xy = (15, 4*p)
		elif item == "tc_fixed_dx":
			xy = (150, 4*p)
		elif item == "st_min_intensity":
			xy = (35, 5*p)
		elif item == "tc_min_pxl":
			xy = (150, 5*p)
		elif item == "btn_remove":
			xy = (15, 6*p)
		elif item == "btn_validate":
			xy = (115, 6*p)
		elif item == "tc_save_name":
			xy = (15, 7*p)
		elif item == "btn_save":
			xy = (70, 8*p)
		elif item == "btn_reverse":
			xy = (50, 9*p)
		elif item == "btn_forward":
			xy = (120, 9*p)
		elif item == "st_frame_display":
			xy = (120, 10*p)
		elif item == "st_image_number":
			xy = (35, 10*p)
		else:
			xy = None
		if xy == None:
			return None
		elif xy[0] < 0:
			return (-1, int(self.user_sreen_size[1]*xy[1]/865))
		elif xy[1] < 0:
			return (int(self.user_sreen_size[0]*xy[0]/1445), -1)
		else:
			return (int(self.user_sreen_size[0]*xy[0]/1445), int(self.user_sreen_size[1]*xy[1]/865))

	def size_of(self, item):
		if item == "ly_image_params":
			xy = (210, 840)
		elif item == "ly_display":
			xy = (1225, 840)
		elif item == "screen":
			xy = (1210,810)
		elif item == "btn_input_dir":
			xy = (120, -1)
		elif item == "cb_ext":
			xy = (60, -1)
		elif item == "tc_fixed_roi_len":
			xy = (50, -1)
		elif item == "tc_fixed_trk_len":
			xy = (50, -1)
		elif item == "tc_fixed_dx":
			xy = (50, -1)
		elif item == "btn_remove":
			xy = (80, -1)
		elif item == "btn_validate":
			xy = (80, -1)
		elif item == "tc_min_pxl":
			xy = (50, -1)
		elif item == "tc_save_name":
			xy = (190, -1)
		elif item == "btn_save":
			xy = (80, -1)
		elif item == "btn_reverse":
			xy = (50, -1)
		elif item == "btn_forward":
			xy = (50, -1)
		else:
			xy = None
		if xy == None:
			return None
		elif xy[0] < 0:
			return (-1, int(self.user_sreen_size[1]*xy[1]/865))
		elif xy[1] < 0:
			return (int(self.user_sreen_size[0]*xy[0]/1445), -1)
		else:
			return (int(self.user_sreen_size[0]*xy[0]/1445), int(self.user_sreen_size[1]*xy[1]/865))

def main():
	app = wx.App()
	ex = ST_GUI()
	ex.Show()
	app.MainLoop()

if __name__ == '__main__':
	main()
