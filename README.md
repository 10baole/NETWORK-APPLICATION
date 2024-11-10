# NETWORK-APPLICATION

Bước 1: Chạy tracker
python tracker.py

Bước 2: Tạo từng node (Tạo nhiều terminal)\n
python node.py -node_id 1
python node.py -node_id 2
python node.py -node_id 3
python node.py -node_id 4

Bước 3: Node 2 muốn download file A thì phải có 1 node nào đó send file A
Terminal node 1: 
send file_A.txt

Terminal node 2: 
download file_A.txt
