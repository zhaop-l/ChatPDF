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

prompt_template_summary = """
我将给你输入一个PDF文件的文本内容，你需要对该文件的内容进行简单总结，100字以内。
输入内容：
"""

prompt_template_question = """
请您根据下面的输入内容，提出三个中文问题，使用{'问题1':,'问题2':,'问题3':}的json格式输出。
输入内容：
"""


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


def chat_glm_api(prompt, temperature=0.85):
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


def chat_with_llm(prompt, input_type, temperature=0.85):
	if input_type == "summary":
		prompt = prompt_template_summary + prompt
		summary = chat_glm(prompt, temperature=temperature)
		return summary
	
	elif input_type == "question":
		prompt = prompt_template_question + prompt
		question_flag = True
		question_list = []
		while question_flag:
			question = chat_glm(prompt, temperature=temperature)
			return_dict = question
			if return_dict[0] != "{":
				return_dict = "{" + return_dict
			if return_dict[-1] != "}":
				return_dict = return_dict + "}"
			new_return_dict = return_dict[:-2].strip()
			if new_return_dict[-1] != "'":
				new_return_dict = new_return_dict + "'}"
			else:
				new_return_dict += "}"
			try:
				b = eval(new_return_dict)
				for key, value in b.items():
					question_list.append(value)
				if len(question_list)>=3:
					question_flag = False
			except Exception as e:
				pass
		return question_list[:3]
	
	else:
		return None


def match_and_ask(query, pdf_data):
	page_find_dict = pdf_embeddings.get_similarity_page(query, pdf_data)
	
	text = ""
	page_number_list = []
	for page_number, page_text in page_find_dict.items():
		page_number_list.append(page_number)
		text += f"第{page_number}页" + "\n" + page_text["text"] + "\n"
	
	prompt = prompt_template.format(context=text, question=query)
	
	answer = chat_glm(prompt)
	# answer = chat_glm_api(prompt)
	return answer,page_number_list[0]
