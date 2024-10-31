import openai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GPT:
    def __init__(self, api_key, model_name, voter=1):
        """
        Initialize the RaLLM class with the OpenAI API key.

        Parameter:
        - api_key (str): Your OpenAI API key.
        - model_name (str): The specific model being used.
        """
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = OpenAI()
        self.model_name = model_name
        self.voter = voter

    # this decorator is used to retry if the rate limits are exceeded
    @retry(
        reraise=True,
        stop=stop_after_attempt(1000),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=(retry_if_exception_type(openai.APITimeoutError)
               | retry_if_exception_type(openai.APIError)
               | retry_if_exception_type(openai.APIConnectionError)
               | retry_if_exception_type(openai.RateLimitError)),
    )
    def get_response(self, complete_prompt):
        """
        This function uses the OpenAI API to code a given sentence based on the provided complete_prompt.

        Parameters:
        - complete_prompt (str): The generated natural language prompt to be sent to the LLM.
        - engine (str): The OpenAI engine to be used for response generation.

        Returns:
        - list of str: The responses from the OpenAI API.
        """
        # See API document at https://beta.openai.com/docs/api-reference/completions/create
        # max tokens: 100 is enough for single question.
        # temperature: 0 for greedy (argmax).
        response = self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=1000,
            messages=[{"role": "user", "content": complete_prompt}],
            temperature=0.0,
            n=self.voter
        )
        return [response.choices[i].message.content for i in range(len(response.choices))]

    def get_contextual_response(self, message_list):
        response = self.client.chat.completions.create(
            model=self.model_name,
            max_tokens=1000,
            messages=message_list,
            temperature=0.0,
            n=self.voter
        )
        return [response.choices[i].message.content for i in range(len(response.choices))]
