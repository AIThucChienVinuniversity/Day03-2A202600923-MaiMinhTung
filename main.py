import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.tools.movie_tool import search_movie_tool
from src.tools.booking_tool import book_movie_tool

from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider


load_dotenv()

all_tools = search_movie_tool + book_movie_tool

def create_provider(provider_name: str, model_name: Optional[str] = None):
    provider_name = provider_name.lower().strip()

    if provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY or GOOGLE_API_KEY. Please set it in .env"
            )

        return GeminiProvider(
            model_name=model_name or "gemini-2.5-flash",
            api_key=api_key
        )

    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "Missing OPENAI_API_KEY. Please set it in .env"
            )

        return OpenAIProvider(
            model_name=model_name or "gpt-4o-mini",
            api_key=api_key
        )

    if provider_name == "local":
        if model_name:
            return LocalProvider(model_name=model_name)
        return LocalProvider()

    raise ValueError(f"Unknown provider: {provider_name}")


def extract_content(response: Any) -> str:
    """
    Provider có thể trả về string hoặc dict.
    GeminiProvider hiện tại trả về dict có key 'content'.
    """
    if isinstance(response, dict):
        return str(response.get("content", ""))

    return str(response)


def run_chatbot(llm, user_input: str) -> Dict[str, Any]:
    system_prompt = """
You are a helpful chatbot.

Answer the user directly.
You do not have access to tools or live web search.
If you are unsure, say that you are unsure.
"""

    raw_response = llm.generate(
        user_input,
        system_prompt=system_prompt
    )

    return {
        "answer": extract_content(raw_response),
        "raw_response": raw_response
    }


def run_agent(llm, user_input: str, chat_history: list = None) -> Dict[str, Any]:
    agent = ReActAgent(
        llm=llm,
        tools=all_tools,
        max_steps=5
    )
    context_input = ""
    if chat_history:
        context_input += "Đây là lịch sử cuộc trò chuyện trước đó, hãy đọc để nắm ngữ cảnh:\n"
        for turn in chat_history:
            context_input += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"
        context_input += "---------------------------------------\n"
    
    context_input += f"Yêu cầu hiện tại của User: {user_input}\n"
    
    # CHỖ NÀY ĐÃ SỬA: Truyền context_input vào thay vì user_input để Agent nhớ bài
    answer = agent.run(context_input)

    return {
        "answer": extract_content(answer),
        "history": getattr(agent, "history", [])
    }


def save_json(data: Dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Day 3 Lab: Chatbot vs ReAct Agent"
    )

    parser.add_argument(
        "--mode",
        choices=["chatbot", "agent"],
        default="agent",
        help="Run chatbot baseline or ReAct agent"
    )

    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "local"],
        default="local",
        help="Choose LLM provider"
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Optional model name, for example gemini-2.5-flash"
    )

    parser.add_argument(
        "--output-json",
        type=str,
        default="outputs/result.json",
        help="Path to save result JSON file"
    )

    args = parser.parse_args()

    llm = create_provider(
        provider_name=args.provider,
        model_name=args.model
    )

    print("=" * 60)
    print(f"Mode     : {args.mode}")
    print(f"Provider : {args.provider}")
    print(f"Model    : {getattr(llm, 'model_name', args.model)}")
    print("=" * 60)

    print("Interactive mode. Type 'exit' to quit.\n")

    chat_history = []

    while True:
        user_input = input("User: ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            print("Bye!")
            break

        if not user_input:
            continue

        if args.mode == "chatbot":
            result = run_chatbot(llm, user_input)
        else:
            result = run_agent(llm, user_input, chat_history)

        output_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": args.mode,
            "provider": args.provider,
            "model": getattr(llm, "model_name", args.model),
            "query": user_input,
            "answer": result.get("answer"),
            "result": result
        }

        print("\nAssistant:")
        print(output_data["answer"])
        print()

        # CHỖ NÀY ĐÃ SỬA: Tạo file output riêng biệt theo thời gian thực để không bị ghi đè
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = Path(args.output_json)
        
        # Biến đổi từ 'outputs/result.json' -> 'outputs/result_20260601_160359.json'
        unique_output_path = base_path.parent / f"{base_path.stem}_{now_str}{base_path.suffix}"

        # Lưu lại vào bộ nhớ chat_history phục vụ câu sau
        chat_history.append({
            "user": user_input,
            "assistant": output_data["answer"]
        })

        if len(chat_history) > 10:
            chat_history.pop(0)

        # Tiến hành lưu file JSON độc lập
        save_json(output_data, str(unique_output_path))
        print(f"Saved JSON to: {unique_output_path}\n")

if __name__ == "__main__":
    main()