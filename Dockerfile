FROM python:3.11-slim-bullseye
LABEL maintainer="nikolai.maltsev@acri-st.fr"
EXPOSE 10000
EXPOSE 8000
ARG WORK_DIR="/opt"
WORKDIR $WORK_DIR
RUN pip install --no-cache-dir aiohttp==3.11.2
COPY src/. ./
RUN chmod +x ./main.sh
CMD ["./main.sh"]
