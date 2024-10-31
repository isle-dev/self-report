import argparse
import csv
import os
from itertools import product
import pandas as pd
import time
import re

from src.prompt import DOMAINS, PERSONALITY_SETTING, BFI_SIMULATION_INSTRUCTION, \
    IPIP_SIMULATION_INSTRUCTION
from src.profile import generate_personal_profile, generate_incontext_prompt
from src.model import GPT
from src.utils import majority_vote


def generate_shape_instructions(profile_save_path, instruction_save_path, questionnaire):
    with open(f"data/{questionnaire}.txt") as item_file:
        item_list = item_file.read().splitlines()

    profile = pd.read_csv(profile_save_path)

    result = list(product(profile['personal_profile'], item_list))

    header = ["personal_profile", "item"]

    with open(instruction_save_path, 'w') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(header)
        writer.writerows(result)


def personality_simulation(args):
    # Initialize the LLM for response generation
    lm = GPT(args.api_key, args.model_name, args.voter)

    # Read instructions from CSV files
    instructions = pd.read_csv(args.instruction_save_path)
    profile_df = pd.read_csv(args.profile_save_path)
    profile_df.set_index('personal_profile', inplace=True)

    # Create the parent directory if it doesn't exist
    parent_directory = os.path.dirname(args.save)
    if not os.path.exists(parent_directory):
        os.makedirs(parent_directory)

    # Iterate through each row of the data
    results = []
    for index, row in instructions.iterrows():
        time.sleep(1)
        # Generate the prompt
        description = row['personal_profile'].strip()

        if 'bfi' in args.questionnaire:
            prompt = BFI_SIMULATION_INSTRUCTION.format(description, row['item'])
        elif 'ipip' in args.questionnaire:
            prompt = IPIP_SIMULATION_INSTRUCTION.format(description, row['item'])

        # Obtain the response
        result_voters = lm.get_response(prompt.strip())
        result = majority_vote(result_voters).strip()
        results.append(result)

        if index == 0:
            print('Example prompt:', prompt)
            print('Response:', result)

        if int(index) % args.batch_size == 0:
            print("Load {}% prompts".format(int(index) / len(instructions) * 100))
            instructions['result'] = pd.Series(results)
            csv_idx = args.save.index('.csv')
            file_name = args.save[:csv_idx] + '_' + str(index) + args.save[csv_idx:]
            instructions.to_csv(file_name, encoding="utf_8_sig", index=False)

    instructions['result'] = pd.Series(results)
    instructions.to_csv(args.save, encoding="utf_8_sig", index=False)

    simulation_post_process(args.save, lm, profile_df, args.questionnaire, args.batch_size)


def match_score(result, questionnaire='bfi'):
    if 'bfi' in questionnaire:
        score_dic = {"disagree strongly": 1, "strongly disagree": 1, "disagree a little":2, "neither agree nor disagree":3,
                     " agree a little": 4, " agree strongly": 5, "strongly agree": 5}
        score_dic_v2 = {"**disagree strongly**": 1, "**strongly disagree**": 1, "**disagree a little**": 2,
                     "**neither agree nor disagree**": 3,
                     "**agree a little**": 4, "**agree strongly**": 5, "**strongly agree**": 5}
    elif 'ipip' in questionnaire:
        score_dic = {"very inaccurate": 1, "moderately inaccurate": 2,
                     "neither accurate nor inaccurate": 3, "moderately accurate": 4, "very accurate": 5}
        score_dic_v2 = {"**very inaccurate**": 1, "**moderately inaccurate**": 2,
                     "**neither accurate nor inaccurate**": 3,
                     "**moderately accurate**": 4, "**very accurate**": 5}

    if isinstance(result, int):
        return result
    elif len(re.findall('\d', result)) == 1:
        return re.findall('\d', result)[0]
    else:
        count = 0
        score_final = 0
        for statement, score in score_dic.items():
            if statement in result.lower():
                count += 1
                # print(count, statement)
                score_final = score
        if count == 1:
            return score_final
        # else:
        #     print(result.lower())

        count = 0
        for statement, score in score_dic.items():
            if f"i {statement}" in result.lower() or f"i \"{statement}\"" in result.lower():
                count += 1
                score_final = score
        if count == 1:
            return score_final

        count = 0
        for statement, score in score_dic_v2.items():
            if statement in result.lower():
                count += 1
                score_final = score
        if count == 1:
            return score_final
        else:
            return result


def add_item(new_result, key, profile, item, result):
    if key not in new_result.keys():
        new_result[profile] = {item: result}
    else:
        new_result[profile][item] = result


def simulation_post_process(processed_file_path, lm, profile_df, questionnaire, batch_size=50, max_trail_num=3, with_instruction = True):
    with open(f'data/{questionnaire}.txt', 'r') as file:
        test_items = [line.strip() for line in file.readlines()]

    result_items = pd.read_csv(processed_file_path)
    new_result = {}
    invalid_num = 0
    count = 0
    for profile, item, result in zip(result_items['personal_profile'], result_items['item'], result_items['result']):
        count += 1
        score = match_score(result, questionnaire)
        key = profile
        if int(count) % batch_size == 0:
            print("Load {}% prompts".format(count / len(result_items['personal_profile']) * 100))
        if isinstance(score, int) or len(score) == 1:
            add_item(new_result, key, profile, item, score)
        else:
            index = 0
            while index < max_trail_num and not isinstance(score, int):
                index += 1
                if with_instruction:
                    description = profile
                else:
                    profile_dic = profile_df.loc[profile]
                    domain = DOMAINS[profile_dic['domain']]
                    description = PERSONALITY_SETTING.format(profile_dic['level'].lower(), domain,
                                                             profile.strip())

                if 'bfi' in args.questionnaire:
                    complete_prompt = BFI_SIMULATION_INSTRUCTION.format(description, item)+"Please indicate the extent to which you agree or disagree on a scale from 1 to 5, rather than the user. Indicate the scale only."
                elif 'ipip' in args.questionnaire:
                    complete_prompt = IPIP_SIMULATION_INSTRUCTION.format(description, item)+"Please select how accurately each statement describes you on a scale from 1 to 5, rather than the user. Indicate the scale only."

                # print(complete_prompt)

                result_voters = lm.get_response(complete_prompt)
                result = majority_vote(result_voters).strip()
                score = match_score(result, questionnaire)

            if isinstance(score, int) or len(score) == 1:
                # print(result)
                add_item(new_result, key, profile, item, score)
            else:
                invalid_num +=1
                print('Invalid:', result)
                add_item(new_result, key, profile, item, result)

    print('Invalid response number:', invalid_num)

    save_path = processed_file_path.split('.csv')[0] + '_processed.csv'
    with open(save_path, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['','domain', 'level'] + test_items)
        for key, value in new_result.items():
            profile_dic = profile_df.loc[key]
            writer.writerow([key, profile_dic['domain'], profile_dic['level']] + list(value.values()))
    print('Processed simulation results have been saved to :', save_path)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--profile_save_path', type=str, default='data/personal_profile.csv')
    argparser.add_argument('--instruction_save_path', type=str, default='output/instruction/ipip_120_instructions_social.csv')
    argparser.add_argument('--save', type=str, default='output/results/ipip_120_simulation_with_instruction/ipip_120_simulation_results_social.csv')

    argparser.add_argument('--task_type', type=str, default='social', choices=['social', 'job', 'public', 'travel', 'inquiry'])
    argparser.add_argument('--questionnaire', type=str, default='ipip_120', choices=['bfi60', 'bfi_xs', 'ipip_120'])

    argparser.add_argument('--model_name', type=str, default='gpt-4o')
    argparser.add_argument('--voter', type=int, default=1)
    argparser.add_argument('--api_key', type=str, default=None)
    argparser.add_argument('--batch_size', type=int, default=50)

    args = argparser.parse_args()

    generate_personal_profile(args.profile_save_path, 10, 5)
    generate_incontext_prompt(args.task_type, args.profile_save_path)

    profile_file_name = args.profile_save_path.split('.')[0]
    incontext_prompt_path = f"{profile_file_name}_{args.task_type}.csv"
    generate_shape_instructions(incontext_prompt_path, args.instruction_save_path, args.questionnaire)

    personality_simulation(args)
