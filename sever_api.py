# -*- coding: utf-8 -*-
# @Time    : 2023/12/3 15:50
# @Author  : zhaop-l(zhaop-l@glocon.com)
import asyncio
import logging
import os
import pickle
import uuid

import datetime
import fitz
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File

from ChatGLM import match_and_ask
from pdf_query import main_pdf_embeddings

app = FastAPI()
upload_directory = 'uploads'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_time():
	now = datetime.datetime.now()
	return now.strftime("%Y-%m-%d %H:%M:%S")


def save_pdf_data(pdf_id, pdf_data):
	data_save_path = os.path.join(upload_directory, f'{pdf_id}.pkl')
	with open(data_save_path, 'wb') as f:
		pickle.dump(pdf_data, f)
	return data_save_path


def load_pdf_data(pdf_id):
	pdf_data_path = os.path.join(upload_directory, f'{pdf_id}.pkl')
	if os.path.isfile(pdf_data_path):
		with open(pdf_data_path, 'rb') as f:
			pdf_data = pickle.load(f)
		return pdf_data
	else:
		return None


def load_pdf_id_dict():
	pkl_list = os.listdir(upload_directory)
	pdf_id_dict = {}
	for i in pkl_list:
		pkl_name = os.path.splitext(i)[0]
		pdf_id_dict[pkl_name] = os.path.join(upload_directory, i)
	
	return pdf_id_dict


def delete_pdf_data(pdf_id):
	pdf_data_path = os.path.join(upload_directory, f'{pdf_id}.pkl')
	if os.path.isfile(pdf_data_path):
		try:
			os.remove(pdf_data_path)
		except Exception as e:
			logger.error(f"Failed to delete PDF data: {e}")
	return pdf_data_path


async def process_uploaded_pdf(file):
	try:
		pdf_data = await file.read()
		pdf_document = fitz.open(stream=pdf_data, filetype='pdf')
		return pdf_document
	except Exception as e:
		logger.error(f"Failed to process uploaded PDF: {e}")
		return None


@app.post("/pdfapi/upload-file")
async def upload_file(file: UploadFile = File(...)):
	try:
		pdf_document = await process_uploaded_pdf(file)
		if pdf_document is None:
			return {'pdfId': None, "message": "Not a valid PDF file", "code": 400, "time": get_current_time()}
		
		pdf_id = f'pdf_{uuid.uuid4()}'
		loop = asyncio.get_event_loop()
		pdf_data = await loop.run_in_executor(None, main_pdf_embeddings, pdf_document)
		# pdf_data = main_chatpdf(pdf_document)
		data_save_path = save_pdf_data(pdf_id, pdf_data)
		
		code = 201 if pdf_data['encode_error'] else 200
		
		return {'pdfId': pdf_id, "message": "Success", "code": code, "time": get_current_time()}
	except Exception as e:
		logger.error(f"Failed to upload file: {e}")
		return {'pdfId': None, "message": "PDF file parsing error", "code": 400, "time": get_current_time()}


@app.post("/pdfapi/chat-pdf")
async def chat_pdf(request: Request):
	try:
		json_post_raw = await request.json()
		# json_post = json.dumps(json_post_raw)
		# json_post_list = json.loads(json_post)
		pdf_id = json_post_raw.get("pdfId", None)
		messages = json_post_raw.get("message", None)
		pdf_id_dict = load_pdf_id_dict()
		
		if pdf_id is None or messages is None:
			return {'pdfId': pdf_id, "message": "pdfId or message is None", "code": 400, "time": get_current_time()}
		
		pdf_data = load_pdf_data(pdf_id)
		
		if pdf_id not in pdf_id_dict or pdf_data is None:
			return {'pdfId': pdf_id, "message": "pdfId is not exist,please upload the file again.", "code": 400,
			        "time": get_current_time()}
		
		result = []
		for message in messages:
			query = message.get("query", None)
			if query:
				loop = asyncio.get_event_loop()
				answer = await loop.run_in_executor(None,match_and_ask,query, pdf_data)
				result.append({'query': query, 'answer': answer})
		
		response = {'data': result, 'pdfId': pdf_id, "message": "Success", "code": 200, "time": get_current_time()}
		return response
	
	except Exception as e:
		logger.error(f"Failed to process PDF chat: {e}")
		return {'pdfId': None, "message": "Failed to process PDF chat", "code": 400, "time": get_current_time()}


@app.post("/pdfapi/delete-pdf")
async def delete_pdf(request: Request):
	try:
		json_post_raw = await request.json()
		pdf_id = json_post_raw.get("pdfId")
		pdf_id_dict = load_pdf_id_dict()
		
		if isinstance(pdf_id, str):
			pdf_id = [pdf_id]
		
		for i in pdf_id:
			if i:
				delete_pdf_data(i)
			
			if i in pdf_id_dict:
				del pdf_id_dict[i]
		
		return {'pdfId': pdf_id, "message": "Success", "code": 200, "time": get_current_time()}
	except Exception as e:
		logger.error(f"Failed to delete PDF: {e}")
		return {'pdfId': None, "message": "Failed to delete PDF", "code": 400, "time": get_current_time()}


if __name__ == '__main__':
	if not os.path.exists(upload_directory):
		os.makedirs(upload_directory)
	
	uvicorn.run(app, host="0.0.0.0", port=8005, workers=1)
