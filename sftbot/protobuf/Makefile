# used to auto-generate Mumble_pb2.py
# (usually you won't need to call this directly)

all: Mumble_pb2.py

clean:
	rm -f Mumble_pb2.py

Mumble_pb2.py: Mumble.proto
	protoc --python_out=. Mumble.proto

.PHONY: all clean
