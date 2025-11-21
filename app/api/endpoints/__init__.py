# from openai import OpenAI
#
# model = "model"
# client = OpenAI(api_key="ragflow-jubLI6vjMitU2tzMx4K0c2_jB4zTsBMLaDnHT8NWD38", base_url=f"http://212.64.10.189:1080/api/v1/chats_openai/86936f54c47f11f097350242ac150006")
#
# stream = True
# reference = True
#
# completion = client.chat.completions.create(
#     model=model,
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "什么是数字电源？"},
#     ],
#     stream=stream,
#     extra_body={"reference": reference}
# )
#
# if stream:
#     for chunk in completion:
#         print(chunk)
#         if reference and chunk.choices[0].finish_reason == "stop":
#             print(f"Reference:\n{chunk.choices[0].delta.reference}")
#             print(f"Final content:\n{chunk.choices[0].delta.final_content}")
# else:
#     print(completion.choices[0].message.content)
#     if reference:
#         print(completion.choices[0].message.reference)