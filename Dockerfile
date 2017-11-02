#FROM warning

FROM python:3-alpine
RUN apk add --update --virtual build-deps build-base ctags git libx11-dev libxpm-dev libxt-dev make ncurses-dev \
    python python-dev && cd /tmp && git clone https://github.com/vim/vim && cd /tmp/vim && ./configure \
    --disable-gui --disable-netbeans --enable-multibyte --enable-pythoninterp --prefix /usr --with-features=big \
    --with-python-config-dir=/usr/lib/python2.7/config && make install && apk del build-deps && apk add \
    libice libsm libx11 libxt ncurses && rm -rf /var/cache/* /var/log/* /var/tmp/* && mkdir /var/cache/apk

WORKDIR /warning

ADD . /warning

#RUN pip install -r requirements.txt

#EXPOSE 9090

CMD ["python", "warning.py"]
