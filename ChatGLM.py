# -*- coding: utf-8 -*-
# @Time    : 2023/12/3 18:59
# @Author  : zhaop-l(zhaop-l@glocon.com)
import json
import requests
from transformers import AutoModel, AutoTokenizer
from pdf_embedding import pdf_embeddings

model_path = r"/data2/LlmModel/chatglm3-6b/"
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(model_path, trust_remote_code=True).cuda()
model = model.eval()

prompt_template = """
基于以下已知信息，简洁和专业的来回答用户的问题。
如果无法从中得到答案，请说 "根据已知信息无法回答该问题" 或 "没有提供足够的相关信息"，不允许在答案中添加编造成分，答案请使用中文。
已知内容:
{context}
问题:
{question}"""


def chat_glm(prompt, max_length=4096, top_p=0.7, temperature=0.7):
	response, history = model.chat(
		tokenizer,
		prompt,
		history=[],
		max_length=max_length,
		top_p=top_p,
		temperature=temperature,
		repetition_penalty=1.2,
	)
	
	return response




def chat_glm_api(prompt,temperature=0.85):
	headers: dict = {"Content-Type": "application/json"}
	url = "http://10.5.171.165:8002"
	response = requests.post(
		url=url,
		data=json.dumps(
			{"prompt": prompt, "max_length": 4096, "history": [], "temperature": temperature}
		),
		headers=headers,
	)
	res = response.json()
	result = res["response"]
	return result


def match_and_ask(query, pdf_data):
	
	page_find_dict = pdf_embeddings.get_similarity_page(query, pdf_data)

	text = ""
	for page_number, page_text in page_find_dict.items():
		text += f"第{page_number}页" + "\n" + page_text["text"] + "\n"
	
	prompt = prompt_template.format(context=text, question=query)
	
	answer = chat_glm(prompt)
	# answer = chat_glm_api(prompt)
	return answer
