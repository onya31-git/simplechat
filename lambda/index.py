import json
import os
import requests

# FastAPI サーバーのエンドポイント
FASTAPI_URL = os.environ.get("FASTAPI_URL", "https://9e90-34-31-253-220.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        user_info = get_authenticated_user(event)
        if user_info:
            print(f"Authenticated user: {user_info}")

        message, conversation_history = parse_event_body(event)
        compiled_prompt = compile_conversation_prompt(message, conversation_history)
        print("Sending prompt:", compiled_prompt)
        
        assistant_response = send_prompt_to_fastapi(compiled_prompt)
        if not assistant_response:
            raise ValueError("No response text from FastAPI")

        update_conversation_history(conversation_history, message, assistant_response)
        
        return success_response(assistant_response, conversation_history)

    except Exception as error:
        print("Error:", str(error))
        return error_response(str(error))


def get_authenticated_user(event):
    """ユーザー情報を認証情報から取得"""
    if 'requestContext' in event and 'authorizer' in event['requestContext']:
        claims = event['requestContext']['authorizer'].get('claims')
        if claims:
            return claims.get('email') or claims.get('cognito:username')
    return None


def parse_event_body(event):
    """リクエストボディを解析し、メッセージと会話履歴を取得"""
    body = json.loads(event.get('body', '{}'))
    return body.get('message'), body.get('conversationHistory', [])


def compile_conversation_prompt(message, conversation_history):
    """会話履歴とメッセージを結合してプロンプトを作成"""
    compiled_prompt = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in conversation_history
    )
    compiled_prompt += f"\nUser: {message}\nAssistant:"
    return compiled_prompt


def send_prompt_to_fastapi(prompt):
    """FastAPI サーバーにプロンプトを送信し、応答を取得"""
    response = requests.post(
        FASTAPI_URL,
        json={
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        raise ValueError(f"FastAPI response error: {response.status_code} - {response.text}")

    response_data = response.json()
    return response_data.get("generated_text", "")


def update_conversation_history(conversation_history, message, assistant_response):
    """会話履歴を更新"""
    conversation_history.append({"role": "user", "content": message})
    conversation_history.append({"role": "assistant", "content": assistant_response})


def success_response(assistant_response, conversation_history):
    """成功レスポンスを返却"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": (
                "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
            ),
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps({
            "success": True,
            "response": assistant_response,
            "conversationHistory": conversation_history
        })
    }


def error_response(error_message):
    """エラーレスポンスを返却"""
    return {
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": (
                "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
            ),
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps({
            "success": False,
            "error": error_message
        })
    }
