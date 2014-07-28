# used to auto-generate Mumble_pb2.py
# (usually you won't need to call this directly)

Mumble_pb2.py: Mumble.proto
	protoc --python_out=. Mumble.proto
