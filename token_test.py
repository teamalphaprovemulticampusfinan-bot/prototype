import os
from dotenv import load_dotenv
from google import genai

# 1. .env 파일에서 API 키 불러오기
load_dotenv()
api_key = os.getenv("GEMINI_PARALLEL_API_KEY")

# 2. Gemini 클라이언트 초기화
client = genai.Client(api_key=api_key)
model_name = "gemini-2.5-flash" # 필요에 따라 "gemini-3.1-flash-lite"로 변경 가능

# 3. 테스트할 프롬프트
prompt = "AlphaProbe 다중 에이전트 환경에서 딥테크 기업의 재무제표를 분석하고 신용을 평가하는 방법 알려줘"

print("--- [방법 A] 사전 토큰 측정 ---")
# API 호출 전 예상 토큰 수 계산
token_count = client.models.count_tokens(
    model=model_name,
    contents=prompt
)
print(f"사전 측정된 입력 토큰: {token_count.total_tokens}\n")

print("--- [방법 B] 실제 API 호출 후 사용량 측정 ---")
# 실제 모델에 프롬프트 전송
response = client.models.generate_content(
    model=model_name,
    contents=prompt
)

# 응답 메타데이터에서 토큰 사용량 추출
usage = response.usage_metadata
print(f"입력(Prompt) 토큰: {usage.prompt_token_count}")
print(f"출력(Candidate) 토큰: {usage.candidates_token_count}")
print(f"총(Total) 토큰: {usage.total_token_count}")


