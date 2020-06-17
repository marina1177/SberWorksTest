#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import load_workbook, Workbook
from  openpyxl.styles import Alignment, PatternFill, Font
import numpy as np
import math
import cmath
from scipy.optimize import root
from os import listdir
from os.path import isfile
from os.path import  join, abspath
import os
import sys
import json

data_files = ['food_coarts.json', 'wifi.json', 'school.json',
              'hosp_child.json', 'hosp_man.json', 'fire_states.json', 'fire_month.json']
data_dir = './data'

class Input(object):
	def __init__(self, state=None):
		self.state = None
		self.street=None
		self.office=None
		self.index=0

class District(object):
	def __init__(self, state=None):
		self.state = None
		self.streets = []

		self.num_school=0
		self.num_hospis=0
		self.num_food_court=0
		self.num_fire=0


def calc_metric(street, data, key):
	# Качество жизни = (#поликлиник (детских) + #образовательных
	# учреждений + #точек общественного питания) / Относительная
	# опасность района,


	print('Найдено совпадение:')
	print(f'{data[key]["state"]}, {key}\n')
	print(f'#поликлиник: {data[key]["num_hosp"]}\n'
	      f'#образовательных учреждений: {data[key]["num_school"]}\n'
	      f'#точек общественного питания: {data[key]["num_food"]}\n')

	if data[key]['num_danger'] == 0:
		print(f'Качество жизни: нет данных\n')
	else:
		q = (data[key]['num_hosp'] + data[key]['num_school'] + data[key]['num_food']) / data[key][
		'num_danger']
		print(f'Качество жизни: {round(q)}\n')

		# ********************VIS**************************************
		# import plotly.plotly as py
		from plotly import graph_objs as go

		title = street + ',' +data[key]["state"] + ',' + key

		fig = go.Figure()
		x = ['hospitals', 'schools', 'food coarts']
		y = [data[key]["num_hosp"], data[key]["num_school"], data[key]["num_food"]]

		fig.add_trace(go.Bar(x=x, y=y, text=str(y), name= title))
		xcoord = [0, 1, 2]
		annotations =[dict(
			x=xi,
			y=yi,
			text=str(yi),
			xanchor='auto',
			yanchor='bottom',
			showarrow=False,
		) for xi, yi in zip(xcoord, y)]

		fig.update_layout(title_text=title, annotations=annotations)
		fig.show()

def init_distr(district, AdmArea, Address):

	if 'num_food' not in district:
		district['num_food'] = 0
	district['num_food'] += 1
	if 'num_school' not in district:
		district['num_school'] = 0
	if 'num_hosp' not in district:
		district['num_hosp'] = 0
	if 'wifi_point' not in district:
		district['wifi_point'] = 0
	if 'num_danger' not in district:
		district['num_danger'] = 0

	if ('state' not in district) & (AdmArea is not None):
		district['state'] = AdmArea
	if 'streets' not in district:
		district['streets'] = []
	street = '.'.join(filter(lambda y: set(y.split()) & {u'улица', u'переулок', u'бульвар', u'шоссе',
	                                                     u'проспект', u'набережная', u'проезд', u'площадь'},
	                         (x.strip() for x in Address.split(u','))))
	if (street is not None) & (street != ''):
		if street not in district['streets']:
			district['streets'].append(street)


def fill_danger(districts,state_data, month_data):
	state_calls = {}
	global_calls = 0

	for i in state_data:
		if (i['AdmArea'] not in state_calls):
			state_calls[i['AdmArea']] = 0
		if (i['Year'] == 2019):
			state_calls[i['AdmArea']] += i['Calls']
	for i in month_data:
		year = int(i['MonthReport'].split()[1])
		if year == 2019:
			#print((year))
			global_calls += i['Calls']
	for i in districts:
		if (districts[i]['state'] in state_calls):
			districts[i]['num_danger'] = round(int(state_calls[districts[i]['state']]*100)/global_calls)



def fill_hospis(districts,data):
	for i in data:
		dot = '..'
		for office in i['ObjectAddress']:
			distr = dot.join(filter(lambda y: set(y.split()) & {u'район', u'поселение', u'поселок'},
			        (x.strip() for x in office['District'].split(u','))))
			if distr is not None:
				if distr not in districts:
					districts[distr] = {}
				init_distr(districts[distr], office['AdmArea'], office['Address'])
				districts[distr]['num_hosp'] += 1


def fill_school(districts,data):
	for i in data:
		dot = '..'
		#print(i['LegalAddress'])
		for office in i['InstitutionsAddresses']:
			distr = dot.join(filter(lambda y: set(y.split()) & {u'район', u'поселение', u'поселок'},
		                        (x.strip() for x in office['District'].split(u','))))
			if distr is not None:
				if distr not in districts:
					districts[distr] = {}
				init_distr(districts[distr], None, office['Address'])
				districts[distr]['num_school'] += 1


def fill_wifi(districts,data):
	for i in data:
		dot = '..'
		distr = dot.join(filter(lambda y: set(y.split()) & {u'район', u'поселение'},
		                        (x.strip() for x in i['District'].split(u','))))
		if distr is not None:
			if distr not in districts:
				districts[distr] = {}
			init_distr(districts[distr], i['AdmArea'], i['Location'])
			districts[distr]['wifi_point'] += 1


def fill_food(data):
	districts = {}

	for i in data:
		dot = '..'
		distr = dot.join(filter(lambda y: set(y.split()) & {u'район', u'поселение'},
		                          (x.strip() for x in i['District'].split(u','))))
		if distr is not None:
			if distr not in districts:
				districts[distr] = {}
			init_distr(districts[distr], i['AdmArea'], i['Address'])
			districts[distr]['num_food'] += 1
	return (districts)

def main():
	#представить имеющиеся данные в удобной форме и создать справочные словари/таблицы(.xlsx)
	#если такие словари уже существуют - обработать входные данные

	file_path = join(data_dir, data_files[0])
	with open(file_path) as f:
	# словарь, в котором хранятся данные для расчета и визуализации метрик
		districts = fill_food(json.load(f))

	file_path = join(data_dir, data_files[1])
	with open(file_path) as f:
		fill_wifi(districts, json.load(f))

	file_path = join(data_dir, data_files[4])
	with open(file_path) as f:
		#data = json.load(f)
		fill_hospis(districts, json.load(f))

	file_path = join(data_dir, data_files[3])
	with open(file_path) as f:
		# data = json.load(f)
		fill_hospis(districts, json.load(f))

	file_path = join(data_dir, data_files[2])
	with open(file_path) as f:
		fill_school(districts, json.load(f))

	file_path = join(data_dir, data_files[5])
	with open(file_path) as f:
		calls_states =  json.load(f)
	file_path = join(data_dir, data_files[6])
	with open(file_path) as f:
		calls_month = json.load(f)
	fill_danger(districts, calls_states, calls_month)

	# for i in districts:
	# 	print(f'{i}:{districts[i]}')

	# Приглашение ввести адрес(улицу)
	addr = str(input('Введите улицу (например Преображенская улица/Сретенский бульвар/проспект Вернадского/) : \n'))
	print(addr)
	cnt = 0
	for i in districts:
		if addr in districts[i]['streets']:
			calc_metric(addr, districts, i)
			cnt +=1
			break
	if cnt == 0:
		print("no data")







#'Address' 'District'






if __name__ == "__main__":
	main()


