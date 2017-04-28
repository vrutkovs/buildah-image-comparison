FROM busybox
RUN mkdir /vol && touch /vol/foo
VOLUME /vol
RUN touch /vol/bar
CMD ["cat", "/vol/bar"]
