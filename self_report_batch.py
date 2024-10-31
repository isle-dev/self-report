import json

import pandas as pd
import argparse

from openai import OpenAI

from self_report import generate_shape_instructions, simulation_post_process
from src.model import GPT
from src.profile import generate_personal_profile, generate_incontext_prompt
from src.prompt import BFI_SIMULATION_INSTRUCTION, IPIP_SIMULATION_INSTRUCTION


def create_request_json_file(args):
    instruction_df = pd.read_csv(args.instruction_save_path)
    request_list = []
    for index, row in instruction_df.iterrows():
        # Generate the prompt
        description = row['personal_profile'].strip()

        if 'bfi' in args.questionnaire:
            prompt = BFI_SIMULATION_INSTRUCTION.format(description, row['item'])
        elif 'ipip' in args.questionnaire:
            prompt = IPIP_SIMULATION_INSTRUCTION.format(description, row['item'])

        if index == 0:
            print(prompt)

        request = {"custom_id": f"request-{index}",
                     "method": "POST",
                     "url": "/v1/chat/completions",
                     "body":{"model": args.model_name,
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.0,
                              "max_tokens": 1000
                              }
                     }
        request_list.append(request)

    # Save to a JSON file
    with open(args.batch_file_save_path, 'w') as json_file:
        for entry in request_list:
            json_file.write(json.dumps(entry) + '\n')


def upload_batch_file(client, batch_file_save_path):
    batch_input_file = client.files.create(
        file=open(batch_file_save_path, "rb"),
        purpose="batch"
    )

    batch_input_file_id = batch_input_file.id

    batch_object = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "self-report personality"
        }
    )

    print("Batch ID", batch_object.id)
    print("output_file_id", batch_object.output_file_id)
    # print("Batch", batch_object)

    batch_status = client.batches.retrieve(batch_object.id)
    print("batch_status", batch_status.status)
    return batch_object.output_file_id


def save_batch_result_json(output_file_id, batch_result_save_path):
    batch_status = client.batches.retrieve(output_file_id)
    print("batch_status", batch_status.status)
    print("output_file_id", batch_status.output_file_id)

    file_response = client.files.content(batch_status.output_file_id)
    response_json_list = []
    for entry in file_response.text.split('\n'):
        if len(entry) > 0:
            response_json_list.append(json.loads(entry))

    with open(batch_result_save_path, 'w') as json_file:
        json.dump(response_json_list, json_file, indent=4)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--profile_save_path', type=str, default='data/personal_profile.csv')
    argparser.add_argument('--api_key', type=str, default=None)
    argparser.add_argument('--instruction_save_path', type=str,
                           default='output/instruction/ipip_120_instructions_travel.csv')
    argparser.add_argument('--batch_file_save_path', type=str,
                           default='output/instruction/ipip_120_instructions_batch_travel.jsonl')
    argparser.add_argument('--batch_result_save_path', type=str,
                           default='output/results/ipip_120_simulation_with_instruction/ipip_120_simulation_results_travel.jsonl')
    argparser.add_argument('--save', type=str,
                           default='output/results/ipip_120_simulation_with_instruction/ipip_120_simulation_results_travel.csv')
    argparser.add_argument('--questionnaire', type=str, default='ipip_120', choices=['bfi60', 'bfi_xs', 'ipip_120'])
    argparser.add_argument('--model_name', type=str, default='gpt-4o')
    argparser.add_argument('--voter', type=int, default=1)

    args = argparser.parse_args()

    if args.api_key:
        client = OpenAI(api_key=args.api_key)
    else:
        client = OpenAI()

    generate_personal_profile(args.profile_save_path, 10, 5)
    generate_incontext_prompt(args.task_type, args.profile_save_path)

    profile_file_name = args.profile_save_path.split('.')[0]
    incontext_prompt_path = f"{profile_file_name}_{args.task_type}.csv"
    generate_shape_instructions(incontext_prompt_path, args.instruction_save_path, args.questionnaire)

    create_request_json_file(args)
    output_file_id = upload_batch_file(client, args.batch_file_save_path)

    # Save result in json format
    save_batch_result_json(output_file_id, args.batch_result_save_path)

    # Save result in csv
    instructions = pd.read_csv(args.instruction_save_path)
    profile_df = pd.read_csv(incontext_prompt_path)
    profile_df.set_index('personal_profile', inplace=True)
    lm = GPT(args.api_key, args.model_name, args.voter)

    with open(args.batch_result_save_path, 'r') as json_file:
        response_json_list = json.load(json_file)

    results = []
    for response in response_json_list:
        results.append(response["response"]["body"]["choices"][0]["message"]["content"])

    instructions['result'] = pd.Series(results)
    instructions.to_csv(args.save, encoding="utf_8_sig", index=False)

    simulation_post_process(args.save, lm, profile_df, args.questionnaire)