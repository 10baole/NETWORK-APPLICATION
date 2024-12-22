# Simple Torrent-like Application (STA)

This repository contains the implementation of a Simple Torrent-like Application (STA) built using custom protocols defined for the project. The application operates over the TCP/IP protocol stack and supports multi-directional data transfer (MDDT), allowing clients to download multiple files from multiple sources simultaneously.

## Application Overview

The STA consists of two main components:
- **Tracker**: A centralized entity that keeps track of nodes and the file pieces they host.
- **Node**: A participant in the network that hosts and shares files.

### Features
1. **Centralized Tracker**: Maintains a directory of file pieces and their locations across nodes.
2. **Node Repository**: Each node informs the tracker about its locally available files but does not transmit file data to the tracker.
3. **File Requests**: Nodes can request files they do not have in their repository. The tracker provides information about nodes hosting the required file pieces.
4. **Multi-Directional Data Transfer (MDDT)**: Supports simultaneous file downloads from multiple source nodes using a multithreaded approach.

## Project Structure

- `configs.py`: Configuration file defining directories, constants, and tracker request modes.
- `messages.py`: Message definitions for communication between nodes and the tracker.
- `node.py`: Implementation of node functionality, including file sharing, downloading, and communication with the tracker.
- `utils.py`: Utility functions for socket management, torrent file generation, logging, and file hashing.

## How It Works

### Tracker Functionality
- The tracker maintains a record of file pieces available across nodes.
- Nodes register themselves with the tracker upon startup.
- When a node requests a file, the tracker responds with information about the nodes hosting the requested file pieces.

### Node Functionality
- Nodes are initialized with a local repository of files.
- Nodes can:
  - **Register** with the tracker to make their files available in the network.
  - **Request** files by sending a request to the tracker.
  - **Download** file pieces from multiple source nodes simultaneously.
  - **Share** file pieces with other nodes in response to their requests.
- Nodes use multithreading to handle simultaneous data transfer for MDDT.

### Multi-Directional Data Transfer (MDDT)
MDDT enables nodes to:
- Split a file into multiple chunks.
- Download these chunks from multiple source nodes concurrently.
- Reassemble the chunks into the complete file upon download completion.

## Usage

### Requirements
- Python 3.x
- Required Python libraries (listed in `requirements.txt`)

### Running the Application
1. Start the tracker (not provided in this repository, but assumed to be running as per the protocol).
2. Start a node:
   ```bash
   python node.py -node_id <NODE_ID> -torrent_file <TORRENT_FILE>
   ```
3. Node Commands:
   - **SEEDING**: Share a file.
     ```
     SEEDING <TORRENT_FILE>
     ```
   - **DOWNLOAD**: Download a file.
     ```
     DOWNLOAD <TORRENT_FILE>
     ```
   - **MAKETORRENT**: Generate a `.torrent` file for a local file.
     ```
     MAKETORRENT <FILE>
     ```

### Example Workflow
1. Generate a `.torrent` file for a file you wish to share:
   ```
   MAKETORRENT example.txt
   ```
2. Register the file with the tracker:
   ```
   SEEDING example.txt.torrent
   ```
3. Another node requests the file:
   ```
   DOWNLOAD example.txt.torrent
   ```

## Implementation Details

### Configuration
- Defined in `configs.py`.
- Includes constants such as:
  - Tracker address and port.
  - Buffer size and chunk size for data transfer.
  - Directories for logs, files, and tracker database.

### Message Protocol
- Messages between nodes and the tracker are encoded as JSON objects.
- Types of messages include:
  - Registration requests.
  - File availability queries.
  - Chunk sharing messages.

### File Sharing and Downloading
- Files are split into chunks of configurable size.
- Chunks are hashed for integrity verification.
- Nodes download chunks in parallel from multiple sources.

## Contributing
Feel free to fork the repository, create a new branch, and submit pull requests for improvements or bug fixes.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments
Special thanks to all contributors for making this project possible.

