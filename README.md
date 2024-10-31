# Can LLM "Self-report"?: Evaluating the Validity of Self-report Scales in Measuring Personality Design in LLM-based Chatbots
This repository contains codes that generate prompts instructing GPT to respond to psychological tests such as BFI-XS, BFI-2 and IPIP-120 when adopting different personalities and roles to perform certain tasks.

### Usage
Run the main script self-report.py to simulate the corresponding personalities and answer the questionnaire. The results will be stored in ./output directory.

### Arguments
You can customize the behavior of the main.py script by modifying the command-line arguments:
```
--profile_save_path: Path to the output CSV file containing the generated profile.
--instruction_save_path: Path to the output CSV file containing the prompt instructions.
--save: Path to the output CSV file where the results will be saved.
--task_type: The task which GPT tends to perform. Choose from 'social', 'job', 'public', 'travel', 'inquiry'.
--questionnaire: The type of psychological personality test used in the experiment. Choose from 'bfi60', 'bfi_xs', 'ipip_120'.
--model_name: The name of the GPT or Claude model to use. The default is 'gpt-4o'.
--voter: The number of generations for each data point. If n > 1, the final code is an aggregation of multiple generations by majority vote. The default is 1.
--api_key: Your API key. If not provided, the script will attempt to use the environment variable.
--batch_size: The batch size used to save the coding progress. The default is 50 (results will be saved for every 50 data points).
```
