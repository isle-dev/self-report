import argparse
import pandas as pd

from src.prompt import BFI_SIMULATION_INSTRUCTION, IPIP_SIMULATION_INSTRUCTION

import tiktoken


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--save', type=str,
                           default='../output/results/bfi60_simulation_with_instruction/bfi60_simulation_results_inquiry.csv')
    # argparser.add_argument('--instruction_save_path', type=str,
    #                        default='../output/instruction/ipip_120_instructions_job.csv')
    argparser.add_argument('--model_name', type=str, default='gpt-4o', choices=['gpt-4o', 'gpt-4'])

    args = argparser.parse_args()

    encoding = tiktoken.encoding_for_model(args.model_name)
    instruction_df = pd.read_csv(args.instruction_save_path)

    token_num = 0
    for idx, row in instruction_df.iterrows():
        description = row['personal_profile']

        if 'bfi' in args.instruction_save_path:
            prompt = BFI_SIMULATION_INSTRUCTION.format(description, row['item'])
        elif 'ipip' in args.instruction_save_path:
            prompt = IPIP_SIMULATION_INSTRUCTION.format(description, row['item'])
            # print(prompt)
        token_num += len(encoding.encode(prompt))

    print(f"instruction_save_path: {args.instruction_save_path}")
    print(f"Token number: {token_num}")

    token_num = 0
    result_df = pd.read_csv(args.save)
    for idx, row in result_df.iterrows():
        # description = row['personal_profile']

        # if 'bfi' in args.instruction_save_path:
        #     prompt = BFI_SIMULATION_INSTRUCTION.format(description, row['item'])
        # elif 'ipip' in args.instruction_save_path:
        #     prompt = IPIP_SIMULATION_INSTRUCTION.format(description, row['item'])
        #     # print(prompt)
        token_num += len(encoding.encode(str(row["result"])))
        # print(row["result"])

    print(f"result_save_path: {args.save}")
    print(f"Token number: {token_num}")

