FROM ubuntu:16.04

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y git netcat curl ca-certificates jq wget tcpdump  iproute2 iputils-ping net-tools telnet iptables
    # apt-get clean && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

# TCP_USER_TIMEOUTを利用する場合はpython3.6以上が必要なので手動でinstallする必要あり

ENV GOVERSION=1.16 GOPATH=/root/go PATH=$PATH:/usr/local/go/bin:/root/go/bin
RUN curl -O https://dl.google.com/go/go${GOVERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GOVERSION}.linux-amd64.tar.gz && \
    rm go${GOVERSION}.linux-amd64.tar.gz && \
    mkdir -p $GOPATH && \
    rm -rf $GOPATH/src $GOPATH/pkg

CMD ["tail", "-f", "/dev/null"]
