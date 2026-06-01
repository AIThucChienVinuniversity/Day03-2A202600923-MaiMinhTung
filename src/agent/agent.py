import os
import re
import json
import ast
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        System prompt that instructs the agent to follow ReAct.
        Includes available tools and format instructions.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t.get('description', 'No description provided')}"
            for t in self.tools
        ])

        return f"""
You are an intelligent ReAct agent.

You can use the following tools:
{tool_descriptions}

You must solve the user's task using this loop:

Thought: explain what you need to do next
Action: tool_name(arguments)
Observation: result of the tool call

Repeat Thought/Action/Observation if needed.

When you have enough information, stop using tools and answer with:

Final Answer: your final response to the user

Important rules:
- Use only tools listed above.
- Do not invent tool names.
- The Action must follow exactly this format: tool_name(arguments)
- Do not wrap the Action in markdown.
- If no tool is needed, directly provide Final Answer.

CRITICAL RULES FOR REASONING:
1. After writing 'Action: tool_name(arguments)', you MUST STOP GENERATING immediately. Do not write 'Observation:' yourself. The system will provide the Observation for you in the next turn.
2. You are NOT ALLOWED to predict or fake the output of any tool.
"""

    def run(self, user_input: str) -> str:
        """
        Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name
        })

        self.history = []

        current_prompt = f"""
User question:
{user_input}

Start reasoning using the ReAct format.
"""

        steps = 0
        final_answer = None

        while steps < self.max_steps:
            logger.log_event("AGENT_STEP_START", {
                "step": steps + 1,
                "prompt": current_prompt
            })

            raw_result = self.llm.generate(
                current_prompt,
                system_prompt=self.get_system_prompt()
            )

            if isinstance(raw_result, dict):
                result = raw_result.get("content", "")
            else:
                result = raw_result

            if result is None:
                result = ""

            result = str(result).strip()

            logger.log_event("LLM_METRIC", {
                "step": steps + 1,
                "llm_output": result
            })

            # Khởi tạo bản ghi history cơ bản cho step hiện tại
            self.history.append({
                "step": steps + 1,
                "llm_output": result,
                "status": "PROCESSING",
                "tool_name": None,
                "tool_args": None,
                "observation": None
            })

            parsed_final = self._parse_final_answer(result)
            if parsed_final:
                final_answer = parsed_final
                self.history[-1]["status"] = "SUCCESS_FINAL_ANSWER"
                logger.log_event("AGENT_FINAL_ANSWER", {
                    "step": steps + 1,
                    "answer": final_answer
                })
                break

            action = self._parse_action(result)

            # Trường hợp 1: LLM không gọi đúng format Action: tool_name(args)
            if action is None:
                logger.log_event("AGENT_NO_ACTION", {
                    "step": steps + 1,
                    "llm_output": result
                })

                # Ghi nhận log lỗi chi tiết vào history
                self.history[-1].update({
                    "status": "FAILED_INVALID_FORMAT",
                    "observation": "No valid Action was found."
                })

                current_prompt += f"""

Assistant output:
{result}

Observation: No valid Action was found. Please either use a valid Action or provide Final Answer.
"""
                steps += 1
                continue

            # Trường hợp 2: Trích xuất action thành công và tiến hành gọi tool
            tool_name, args = action
            observation = self._execute_tool(tool_name, args)

            logger.log_event("TOOL_EXECUTION", {
                "step": steps + 1,
                "tool_name": tool_name,
                "args": args,
                "observation": observation
            })

            # Cập nhật thông tin chi tiết của tool chạy thành công vào history
            self.history[-1].update({
                "status": "TOOL_EXECUTED",
                "tool_name": tool_name,
                "tool_args": args,
                "observation": observation
            })

            current_prompt += f"""

Assistant output:
{result}

Observation: {observation}

Continue. If you have enough information, provide Final Answer.
"""
            steps += 1

        logger.log_event("AGENT_END", {
            "steps": steps,
            "final_answer": final_answer
        })

        if final_answer:
            return final_answer

        return "I could not complete the task within the maximum number of steps."
        """
        Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name
        })

        self.history = []

        current_prompt = f"""
User question:
{user_input}

Start reasoning using the ReAct format.
"""

        steps = 0
        final_answer = None

        while steps < self.max_steps:
            logger.log_event("AGENT_STEP_START", {
                "step": steps + 1,
                "prompt": current_prompt
            })

            raw_result = self.llm.generate(
                current_prompt,
                system_prompt=self.get_system_prompt()
            )

            if isinstance(raw_result, dict):
                result = raw_result.get("content", "")
            else:
                result = raw_result

            if result is None:
                result = ""

            result = str(result).strip()

            logger.log_event("LLM_METRIC", {
                "step": steps + 1,
                "llm_output": result
            })

            self.history.append({
                "step": steps + 1,
                "llm_output": result
            })

            parsed_final = self._parse_final_answer(result)
            if parsed_final:
                final_answer = parsed_final
                logger.log_event("AGENT_FINAL_ANSWER", {
                    "step": steps + 1,
                    "answer": final_answer
                })
                break

            action = self._parse_action(result)

            if action is None:
                logger.log_event("AGENT_NO_ACTION", {
                    "step": steps + 1,
                    "llm_output": result
                })

                current_prompt += f"""

Assistant output:
{result}

Observation: No valid Action was found. Please either use a valid Action or provide Final Answer.
"""
                steps += 1
                continue

            tool_name, args = action

            observation = self._execute_tool(tool_name, args)

            logger.log_event("TOOL_EXECUTION", {
                "step": steps + 1,
                "tool_name": tool_name,
                "args": args,
                "observation": observation
            })

            # --- ĐOẠN MÃ ĐÃ ĐƯỢC THÊM VÀO ĐÂY ---
            self.history[-1]["tool_name"] = tool_name
            self.history[-1]["tool_args"] = args
            self.history[-1]["observation"] = observation
            # ------------------------------------

            current_prompt += f"""

Assistant output:
{result}

Observation: {observation}

Continue. If you have enough information, provide Final Answer.
"""

            steps += 1

        logger.log_event("AGENT_END", {
            "steps": steps,
            "final_answer": final_answer
        })

        if final_answer:
            return final_answer

        return "I could not complete the task within the maximum number of steps."

    def _parse_final_answer(self, text: str) -> Optional[str]:
        """
        Extract Final Answer from LLM output.
        """
        match = re.search(
            r"Final Answer\s*:\s*(.*)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            return match.group(1).strip()

        return None

    def _parse_action(self, text: str) -> Optional[tuple]:
        """
        Extract Action from LLM output.

        Expected format:
        Action: tool_name(arguments)
        """
        text = self._remove_markdown_code_fences(text)

        match = re.search(
            r"Action\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return None

        tool_name = match.group(1).strip()
        args = match.group(2).strip()

        return tool_name, args

    def _remove_markdown_code_fences(self, text: str) -> str:
        """
        Remove ```json or ``` wrappers if the LLM outputs markdown.
        """
        text = text.strip()

        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return text.strip()

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Execute tools by name.
        """
        for tool in self.tools:
            if tool["name"] != tool_name:
                continue

            func = (
                tool.get("func")
                or tool.get("function")
                or tool.get("callable")
            )

            if func is None:
                return f"Tool {tool_name} exists, but no callable function is attached."

            try:
                parsed_args, parsed_kwargs = self._parse_tool_args(args)

                result = func(*parsed_args, **parsed_kwargs)

                if isinstance(result, (dict, list)):
                    return json.dumps(result, ensure_ascii=False)

                return str(result)

            except Exception as e:
                return f"Error while executing tool {tool_name}: {str(e)}"

        return f"Tool {tool_name} not found."

    def _parse_tool_args(self, args: str):
        """
        Parse tool arguments from a string.
        """
        args = args.strip()

        if not args:
            return [], {}

        if args.startswith("{") and args.endswith("}"):
            data = json.loads(args)
            if isinstance(data, dict):
                return [], data
            return [data], {}

        try:
            tree = ast.parse(f"f({args})", mode="eval")
            call = tree.body

            parsed_args = [
                ast.literal_eval(arg)
                for arg in call.args
            ]

            parsed_kwargs = {
                kw.arg: ast.literal_eval(kw.value)
                for kw in call.keywords
            }

            return parsed_args, parsed_kwargs

        except Exception:
            return [args], {}