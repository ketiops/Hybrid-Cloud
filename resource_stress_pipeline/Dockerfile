FROM nvidia/cuda:11.2.2-cudnn8-devel-ubuntu18.04

RUN echo 'export PATH=/usr/local/cuda-11.2bin${PATH:+:${PATH}}' >> ~/.bashrc
RUN echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.2/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> ~/.bashrc
RUN echo 'export PATH=/usr/local/cuda/bin:/$PATH' >> ~/.bashrc
RUN echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> ~/.bashrc

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential python-numpy python3-numpy stressapptest

COPY ./src /app
COPY requirements.txt /app
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3"]
CMD ["main.py"]
