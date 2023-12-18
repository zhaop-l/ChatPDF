# -*- coding: utf-8 -*-
# @Time    : 2023/12/3 18:25
# @Author  : zhaop-l(zhaop-l@glocon.com)
from sentence_transformers import SentenceTransformer, util
import torch

class PDF_Embeddings:
	def __init__(self):
		self.model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
	
	def get_text_embedding(self, pdf_text):
		embeddings_t = self.model.encode(pdf_text).cpu()
		torch.cuda.empty_cache()
		torch.cuda.ipc_collect()
		print("embedding finish.")
		return embeddings_t
	
	def get_similarity_page(self, query, pdf_data):
		text_chunk_embeddings = pdf_data['text_chunk_embeddings']
		text_chunk_list = pdf_data['text_chunk_list']
		page_text_chunk_index = pdf_data['text_chunk_index']
		page_info_dict = pdf_data['page_info_dict']
		top_k = 2
		input_embedding = self.model.encode([query])
		scores = (
			util.dot_score(input_embedding, text_chunk_embeddings)[0]
			.cpu()
			.tolist()
		)
		doc_score_pairs = list(zip(text_chunk_list, scores))
		
		# Sort by decreasing score
		doc_score_pairs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
		
		# for i, score in doc_score_pairs[:top_k]:
		# 	print(score, text_chunk_list[i], page_text_chunk_index[i])
		
		top_k_index = [index for index, _ in doc_score_pairs[:top_k]]
		page_numbers = []
		page_find = {}
		for i in top_k_index:
			page_number = page_text_chunk_index[i]
			if page_number not in page_numbers:
				page_numbers.append(page_number)
				page_find[page_number] = page_info_dict[page_number]
		
		return page_find


pdf_embeddings = PDF_Embeddings()
