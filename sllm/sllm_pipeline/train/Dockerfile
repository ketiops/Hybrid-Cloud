FROM rootmo/preprocess:1.3

ENV DIR /home/sllm_pipeline

WORKDIR ${DIR}

RUN mkdir -p ${DIR} ${DIR}/datasets
RUN chmod 777 ${DIR} ${DIR}/datasets

COPY finetune.py .

ENTRYPOINT ["python3", "finetune.py"]
CMD ["--base_model", "baffo32/decapoda-research-llama-7B-hf", \
    "--output_dir", "./datasets", \
    "--batch_size","128", \
    "--micro_batch_size", "4", \
    "--num_epochs", "3", \
    "--learning_rate", "1e-4", \
    "--cutoff_len", "512", \
    "--val_set_size", "2000", \
    "--lora_r", "8", \
    "--lora_alpha", "16", \
    "--lora_dropout", "0.05", \
    "--lora_target_modules", "[q_proj,v_proj]", \
    "--train_on_inputs", \
    "--group_by_length"]