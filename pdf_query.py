# -*- coding: utf-8 -*-
# @Time    : 2023/12/3 17:59
# @Author  : zhaop-l(zhaop-l@glocon.com)

from collections import Counter
from tqdm import tqdm
from pdf_embedding import pdf_embeddings


def bbox_overlap(bbox1, bbox2):
	# bbox1 和 bbox2 分别为两个边界框的坐标 [x1, y1, x2, y2]
	x1_1, y1_1, x2_1, y2_1 = bbox1
	x1_2, y1_2, x2_2, y2_2 = bbox2
	
	# 判断两个边界框是否有水平和垂直方向上的重叠
	if x1_1 <= x2_2 and x2_1 >= x1_2 and y1_1 <= y2_2 and y2_1 >= y1_2:
		return True
	else:
		return False


def replace_text(text):
	# 去除每个子列表中的换行符
	for sublist in text:
		for i in range(len(sublist)):
			if isinstance(sublist[i], str):
				sublist[i] = sublist[i].replace("\n", "")
	return text


def table_to_markdown(table):
	markdown = "|"
	for header in table[0]:
		markdown += " " + str(header) + " |"
	markdown += "\n|"
	for _ in range(len(table[0])):
		markdown += " --- |"
	markdown += "\n"
	for row in table[1:]:
		markdown += "|"
		for item in row:
			markdown += " " + str(item) + " |"
		markdown += "\n"
	return markdown


def get_page_info(doc, page_number):
	page = doc.load_page(page_number)
	lines_width = []
	x0_list = []
	text_list = []
	font_size_list = []
	doc_dict = page.get_text("dict", sort=True)
	
	width = doc_dict["width"]
	height = doc_dict["height"]
	doc_blocks = doc_dict["blocks"]
	
	page_info = []
	images_bbox = []
	tables_bbox = []
	tables_record = []
	try:
		doc_tabs = page.find_tables()
		tabs_count = len(doc_tabs.tables)
	except Exception as e:
		tabs_count = 0
	if tabs_count > 0:
		for i, table in enumerate(doc_tabs):
			tables_bbox.append({"number": i, "bbox": table.bbox, "text": replace_text(table.extract())})
	images_list = page.get_image_info()
	if len(images_list) > 0:
		for image in images_list:
			image_bbox = image.get("bbox")
			
			if image_bbox:
				image_wide = image_bbox[2] - image_bbox[0]
				image_height = image_bbox[3] - image_bbox[1]
				if abs(image_wide - width) > 10 and abs(image_height - height) > 10:
					images_bbox.append(image_bbox)
	
	for i in range(len(doc_blocks)):
		doc_block = doc_blocks[i]
		block_type = doc_block["type"]
		block_bbox = doc_block["bbox"]
		is_overlap_table = False
		is_overlap_image = False
		if tabs_count > 0:
			for tab in tables_bbox:
				tab_number = tab["number"]
				tab_bbox = tab["bbox"]
				tab_info = tab["text"]
				is_overlap_table = bbox_overlap(tab_bbox, block_bbox)
				if is_overlap_table:
					if tab_number not in tables_record:
						tables_record.append(tab_number)
						page_info.append(
							{"page_number": page_number + 1, "type": 2, "number": tab_number, "bbox": tab_bbox,
							 "text": tab_info})
					break
		if len(images_bbox) >= 1:
			for image_bbox in images_bbox:
				is_overlap_image = bbox_overlap(image_bbox, block_bbox)
				if is_overlap_image:
					if block_type == 1:
						page_info.append({"page_number": page_number + 1, "type": 1, "bbox": image_bbox})
					break
		if is_overlap_image or is_overlap_table:
			continue
		if block_type == 0:
			block_lines = doc_block["lines"]
			origin_y = 0
			for j in range(len(block_lines)):
				block_line = block_lines[j]
				line_spans = block_line["spans"]
				line_bbox = block_line["bbox"]
				y0 = round(line_bbox[1], 2)
				line_width = round(int(line_bbox[2]) - int(line_bbox[0]), 2)
				x0 = int(line_bbox[0])
				x0_list.append(x0)
				lines_width.append(line_width)
				line_text = ""
				line_dict = {"size": 0, "font": [], "line_width": line_width, "bbox": line_bbox, "text": ""}
				line_size = 0
				for k in range(len(line_spans)):
					line_span = line_spans[k]
					span_size = round(line_span["size"], 2)
					if span_size > line_size:
						line_size = span_size
					span_text = line_span["text"]
					line_text = line_text + span_text
				line_dict["size"] = line_size
				line_dict["text"] = line_text
				font_size_list.append(line_size)
				if y0 - origin_y > 1:
					page_info.append({"page_number": page_number + 1, "type": 0, "line_width": line_width, "x0": x0,
					                  "line_size": line_size, "text": line_text})
					text_list.append(line_text)
				else:
					if j >= 1:
						page_info[-1]["text"] = page_info[-1]["text"] + "\t" + line_dict["text"]
						page_info[-1]["line_width"] = page_info[-1]["line_width"] + line_width
						text_list[-1] = page_info[-1]["text"]
	return page_info, lines_width, x0_list, text_list, font_size_list


def get_constant(lines_width, x0_list, font_size_list, text_list, page_info):
	line_width_mode = Counter(lines_width).most_common(1)[0][0]
	x0_mode = Counter(x0_list).most_common(1)[0][0]
	font_size_cunt = Counter(font_size_list)
	text_list_count = Counter(text_list)
	duplicate_rows = []
	for i, j in text_list_count.items():
		if j >= 5:
			duplicate_rows.append(i)
	
	effective_font_size = []
	for i, j in font_size_cunt.items():
		if j > len(page_info) // 5:
			effective_font_size.append(i)
	font_size_mode = font_size_cunt.most_common(1)[0][0]
	print(f"""
	line width : {line_width_mode}
	x0 : {x0_mode}
	font size : {font_size_mode}
	duplicate rows : {duplicate_rows}
	effective font size : {effective_font_size}
	""")
	
	return line_width_mode, x0_mode, font_size_mode, duplicate_rows, effective_font_size


def get_line_type(pdf_info, line_width_mode, x0_mode, font_size_mode, duplicate_rows, effective_font_size):
	new_pdf_info1 = []
	directory_text = ""
	directory_page_number = 0
	directory_flag = False
	directory_line_width = []
	for i, page_info in enumerate(pdf_info):
		page_text1 = []
		for j, line_info in enumerate(page_info):
			line_type = line_info["type"]
			page_number = line_info["page_number"]
			if line_type == 0:
				line_text = line_info["text"]
				line_width = line_info["line_width"]
				line_size = line_info["line_size"]
				line_x0 = line_info["x0"]
				line_description = ""
				line_text_flag = -1
				if directory_flag and page_number == directory_page_number:
					if line_width not in directory_line_width:
						directory_line_width.append(line_width)
					
					line_description = "directory"
					directory_text += "\n" + line_text
					page_text1.append({"page_number": page_number, "text": line_text, "type": line_description,
					                   "text_flag": line_text_flag})
					continue
				
				elif directory_flag and page_number <= directory_page_number + 2:
					if line_width in directory_line_width:
						directory_text += "\n" + line_text
						line_description = "directory"
						page_text1.append({"page_number": page_number, "text": line_text, "type": line_description,
						                   "text_flag": line_text_flag})
						continue
					else:
						directory_flag = False
				else:
					directory_flag = False
				
				if line_text in duplicate_rows or line_size not in effective_font_size:
					continue
				elif "目录" in line_text:
					directory_flag = True
					directory_text += line_text
					directory_page_number = page_number
					line_description = "directory"
				elif abs(line_x0 - x0_mode) == 0:
					if abs(line_width - line_width_mode) <= line_size * 3:
						line_description = "text"
						line_text_flag = 2
					elif line_text in directory_text:
						line_description = "title"
					elif "." in line_text and "。" not in line_text and "；" not in line_text:
						line_description = "title"
					elif "。" in line_text or "；" in line_text or "：" in line_text:
						line_description = "text"
						line_text_flag = 3
					else:
						line_description = "text"
						line_text_flag = 3
				elif 0 < abs(line_x0 - x0_mode) <= line_size * 3:
					if abs(line_width - line_width_mode) <= line_size * 3:
						line_description = "text"
						line_text_flag = 1
					else:
						line_description = "title"
				elif abs(line_x0 - x0_mode) >= line_size * 3 and line_width > 2 * line_size:
					if "图" in line_text:
						line_description = "image name"
					elif "表" in line_text:
						line_description = "table name"
					else:
						line_description = "clutter"
				else:
					if line_width < 2 * line_size:
						continue
					else:
						line_description = "clutter"
				if line_description == "":
					print(line_info)
				page_text1.append({"page_number": page_number, "text": line_text, "type": line_description,
				                   "text_flag": line_text_flag})
			elif line_type == 1:
				page_text1.append({"page_number": page_number, "text": "", "type": "image", "text_flag": -1})
			elif line_type == 2:
				if len(page_text1) == 0:
					line_text_flag = 2
				else:
					line_text_flag = 1
				page_text1.append({"page_number": page_number, "text": line_info["text"], "type": "table",
				                   "text_flag": line_text_flag})
		new_pdf_info1 += page_text1
	return new_pdf_info1


def check_table_image(new_pdf_info1):
	new_pdf_info2 = []
	for i, line_info in enumerate(new_pdf_info1):
		page_number = line_info["page_number"]
		line_text = line_info["text"]
		if line_info["type"] == "table":
			if line_info["text_flag"] == 1:
				if new_pdf_info1[i - 1]["type"] not in ["table name", "table", "image"]:
					new_pdf_info2[-1]["type"] = "table name"
				
				new_pdf_info2.append(line_info)
			elif line_info["text_flag"] == 2:
				j = 1
				while j < len(new_pdf_info2):
					if new_pdf_info2[-j]["type"] == "table":
						if line_text[0] == new_pdf_info2[-j]["text"][0]:
							new_pdf_info2[-j]["text"] += line_text[1:]
						else:
							new_pdf_info2[-j]["text"] += line_text[:]
						break
					elif new_pdf_info2[-j]["type"] == "table name":
						previous_page_number = new_pdf_info2[-j]["page_number"]
						line_info["page_number"] = previous_page_number
						if j == 1:
							new_pdf_info2.append(line_info)
						else:
							new_pdf_info2.insert(-j + 1, line_info)
						break
					else:
						j += 1
		elif line_info["type"] == "image":
			if i < len(new_pdf_info1) - 1:
				if new_pdf_info1[i + 1]["type"] not in ["image name", "image", "table", "table name"] and \
						new_pdf_info1[i + 1]["page_number"] == page_number:
					new_pdf_info1[i + 1]["type"] = "image name"
		else:
			new_pdf_info2.append(line_info)
	return new_pdf_info2


def get_page_info_dict(new_pdf_info2):
	page_info_dict = {}
	for i, line_info in enumerate(new_pdf_info2):
		page_number = line_info["page_number"]
		if page_number not in page_info_dict.keys():
			page_info_dict[page_number] = {"text": ""}
		line_text = line_info["text"]
		if line_info["type"] == "table":
			markdoewn_table = table_to_markdown(line_text)
			page_info_dict[page_number]["text"] += markdoewn_table if page_info_dict[page_number][
				                                                          "text"] == "" else "\n" + markdoewn_table
		elif line_info["type"] == "directory":
			page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
				                                                    "text"] == "" else "\n" + line_text
		elif line_info["type"] == "title":
			page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
				                                                    "text"] == "" else "\n" + line_text
		elif line_info["type"] == "text":
			if line_info["text_flag"] == 1:
				page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
					                                                    "text"] == "" else "\n" + line_text
			elif line_info["text_flag"] == 2:
				if page_info_dict[page_number]["text"] == "":
					if page_number - 1 in page_info_dict:
						page_info_dict[page_number - 1]["text"] += line_text
					else:
						page_info_dict[page_number]["text"] += line_text
				else:
					page_info_dict[page_number]["text"] += line_text
			elif line_info["text_flag"] == 3:
				if page_info_dict[page_number]["text"] == "":
					if page_number - 1 in page_info_dict:
						page_info_dict[page_number - 1]["text"] += line_text
					else:
						page_info_dict[page_number]["text"] += line_text
				else:
					page_info_dict[page_number]["text"] += line_text
		elif line_info["type"] == "table name":
			page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
				                                                    "text"] == "" else "\n" + line_text
		elif line_info["type"] == "image name":
			page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
				                                                    "text"] == "" else "\n" + line_text
		elif line_info["type"] == "clutter":
			page_info_dict[page_number]["text"] += line_text if page_info_dict[page_number][
				                                                    "text"] == "" else "\n" + line_text
		else:
			print(line_info)
	return page_info_dict


def get_text_chunk(page_info_dict, chunk_size=400):
	page_text_chunk_dict = {}
	for page_number, page_text in page_info_dict.items():
		text = page_text["text"]
		text_list = []
		if len(text) > chunk_size:
			text_list_linebreak = text.split("\n")
			for i, item in enumerate(text_list_linebreak):
				if len(item) > chunk_size:
					text_list_period = item.split("。")
					for j, item_item in enumerate(text_list_period):
						if item_item != "":
							text_list.append(item_item + "。")
				else:
					text_list.append(item)
		else:
			text_list.append(text)
		page_text_chunk_dict[page_number] = text_list
	return page_text_chunk_dict


def main_pdf_embeddings(pdf_doc):
	doc = pdf_doc
	total_pages = doc.page_count
	pdf_info = []
	x0_list = []
	lines_width = []
	text_list = []
	font_size_list = []
	
	for i in tqdm(range(total_pages)):
		page_info, l_width, x0, texts, fone_size = get_page_info(doc, i)
		lines_width += l_width
		x0_list += x0
		text_list += texts
		font_size_list += fone_size
		if len(page_info) >= 1:
			pdf_info.append(page_info)
	
	print("有效总页数：", len(pdf_info))
	
	line_width_mode, x0_mode, font_size_mode, duplicate_rows, effective_font_size = get_constant(lines_width, x0_list,
	                                                                                             font_size_list,
	                                                                                             text_list, pdf_info)
	encode_error = False
	for i in duplicate_rows:
		try:
			i.encode('gb2312')
		except:
			encode_error = True
			break
	new_pdf_info1 = get_line_type(pdf_info, line_width_mode, x0_mode, font_size_mode, duplicate_rows,
	                              effective_font_size, )
	new_pdf_info2 = check_table_image(new_pdf_info1)
	page_info_dict = get_page_info_dict(new_pdf_info2)
	
	page_text_chunk_dict = get_text_chunk(page_info_dict)
	page_text_chunk_list = []
	page_text_chunk_index = []
	for page_number, page_text in page_text_chunk_dict.items():
		for i in page_text:
			page_text_chunk_list.append(i)
			page_text_chunk_index.append(page_number)
	
	page_text_chunk_embeddings = pdf_embeddings.get_text_embedding(page_text_chunk_list)
	
	return {'text_chunk_embeddings': page_text_chunk_embeddings, 'text_chunk_list': page_text_chunk_list,
	        'text_chunk_index': page_text_chunk_index, 'page_info_dict': page_info_dict, 'encode_error': encode_error,}
