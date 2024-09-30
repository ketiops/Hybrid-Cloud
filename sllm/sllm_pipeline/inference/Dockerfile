FROM rootmo/preprocess:1.3

ENV DIR /home/sllm_pipeline

WORKDIR ${DIR}

RUN mkdir -p ${DIR} ${DIR}/datasets
RUN chmod 777 ${DIR} ${DIR}/datasets

COPY input.json .
COPY generator.py .

ENTRYPOINT ["python3", "generator.py"]
CMD ["--load_8bit", \
    "--base_model", "baffo32/decapoda-research-llama-7B-hf", \
    "--lora_weights", "./datasets"]