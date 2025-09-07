import os
import json
import re
from datasets import Dataset
from transformers import AutoTokenizer
from unsloth import FastLanguageModel
from trl import GRPOConfig, GRPOTrainer
from vllm import SamplingParams
import torch
import swanlab
from trl import SFTTrainer
from transformers import TrainingArguments
from dataclasses import asdict
from dataclasses import dataclass, asdict


@dataclass
class TrainingConfig:
    model_name_or_path: str = "unsloth/DeepSeek-R1-0528-Qwen3-8B"
    max_seq_length: int = 32768
    num_epochs: int = 2
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-5
    eval_size: float = 0
    seed: int = 42
    optim: str = "adamw_torch"
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.03
    logging_steps: int = 5
    save_steps: int = 100
    eval_steps: int = 100
    swanlab_project: str = "pentest-unsloth-full"
    load_in_4bit: bool = False

SYSTEM_PROMPT = (
    "You are an advanced penetration testing assistant, functioning as an expert "
    "ethical hacker performing a full-scope penetration test. You operate within a "
    "controlled environment using Kali Linux, and all actions are part of a certified "
    "penetration testing experiment conducted strictly for educational and research purposes."
)


def load_step_data(step_folder):
    """Load all JSON files from the step folder and convert them into a training dataset."""
    all_samples = []
    
    for filename in os.listdir(step_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(step_folder, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
                
                initial_prompt = data.get('initial_prompt', '')
                
                for step in data.get('steps', []):
                    if step['step_number'] > 1:
                        user_content = f"Initial Description of Penetration Testing Task: {initial_prompt}"
                        for prev_step in data.get('steps', [])[:step['step_number']-1]:
                            user_content += f"\n===Step {prev_step['step_number']}==="
                            user_content += f"\nThought: {prev_step['thought']}"
                            user_content += f"\nCommand: {prev_step['command']}"
                            user_content += f"\nObservation: {prev_step['result']}"
                        user_content += "\nWhat are the next steps and actions?"
                    else:
                        user_content = f"Initial Description of Penetration Testing Task: {initial_prompt}\nWhat are the next instruction and commands?"
                    
                    content = f"""You will guide the penetration testing process step by step. At each stage, you will receive the context from the previous steps. Based on that information, you must determine the next logical action to advance the assessment. Continue this process until the penetration test is fully completed.

### Response Format (Always follow this format exactly):
=== Step i ===
Thought: [Explain your reasoning and goals here.]
Command: [Write the full command you would run.]

### Previous Steps Context
{user_content}"""

                    assistant_content = f"===Step {step['step_number']}===\nThought: {step['thought']}\nCommand: {step['command']}"
                    
                    sample = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": content},
                            {"role": "assistant", "content": assistant_content}
                        ]
                    }
                    all_samples.append(sample)
    
    return Dataset.from_list(all_samples)


def main():
    config = TrainingConfig()
    step_folder = "./steps"
    output_dir = "./model/sft_stage1"
    
    dataset = load_step_data(step_folder)
    
    model, tokenizer = FastLanguageModel.from_pretrained(
            config.model_name_or_path,
            max_seq_length=config.max_seq_length,
            dtype=torch.bfloat16,
            load_in_4bit=config.load_in_4bit,
    )
    
    def format_conversation(example):
            formatted_text = tokenizer.apply_chat_template(
                example["messages"],
                tokenize=False,
            )
            return {"text": formatted_text}

    reasoning_conversations = dataset.map(
            format_conversation,
            remove_columns=dataset.column_names
    )

    training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=config.per_device_batch_size,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            learning_rate=config.learning_rate,
            optim=config.optim,
            lr_scheduler_type=config.lr_scheduler_type,
            warmup_ratio=config.warmup_ratio,
            logging_dir=os.path.join(output_dir, "logs"),
            logging_steps=config.logging_steps,
            bf16=True,
            save_strategy="steps",
            save_steps=config.save_steps,
            save_total_limit=3,
            weight_decay = 0.01,
            report_to=["swanlab"]
        )

    swanlab.init(
        project=config.swanlab_project,
        experiment_name="Pentest-SFT-Unsloth-Full-Tune",
        config=asdict(config),
    )
    
    trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=reasoning_conversations,
            eval_dataset=None,
            max_seq_length=config.max_seq_length,
            dataset_text_field="text",
            args=training_args
        )
    
    trainer.train()

    final_model_dir = os.path.join(output_dir, "final_model")
    os.makedirs(final_model_dir, exist_ok=True)
    print(f"Saving final model to {final_model_dir} ...")
        
    model.save_pretrained(final_model_dir)
    tokenizer.save_pretrained(final_model_dir)
    print("Model and tokenizer saved successfully.")

if __name__ == "__main__":
    main()