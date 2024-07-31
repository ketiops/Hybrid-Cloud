FROM thebloke/cuda11.8.0-ubuntu22.04-pytorch

ENV DIR /home/sllm_pipeline

RUN mkdir -p ${DIR} ${DIR}/datasets 

WORKDIR ${DIR}

COPY requirements.txt .
COPY alpaca.json .
COPY data_preprocess.py .

RUN pip3 install -r requirements.txt
RUN pip3 uninstall peft -y -q
RUN pip3 install peft==0.10.0

ENTRYPOINT ["python3", "data_preprocess.py"]
CMD ["--base_model", "baffo32/decapoda-research-llama-7B-hf", \
    "--data_path", "yahma/alpaca-cleaned", \
    "--cutoff_len", "512", \
    "--val_set_size", "2000", \
    "--train_on_inputs"]