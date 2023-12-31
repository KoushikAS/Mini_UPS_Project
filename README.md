# Mini-UPS Project

## Overview

This Mini-UPS project is a Python-based implementation of a simplified UPS-like shipping system. It is designed to interact with a simulated world server, managing the logistics of package delivery through a network of warehouses and trucks. The project demonstrates handling real-time shipping operations, including package tracking, delivery status updates, and coordination with warehouses. This works in conjuction with Mini-Amazon and World Simulator.

## Features

- **Server Communication:** Connects to a simulated world server to manage package deliveries.
- **Package Handling:** Processes package orders, including tracking, loading, and delivery.
- **Real-time Status Updates:** Provides up-to-date information on package location and delivery status.
- **Warehouse Coordination:** Manages interactions with warehouses for package pick-up and loading.
- **Truck Fleet Management:** Controls a fleet of trucks for efficient package delivery.

## Installation and Running

### Prerequisites
- Docker
  
### Installation
1. Clone the repository to your local machine:

```sh
git clone https://github.com/KoushikAS/Mini_UPS_Project.git
cd Mini_UPS_Project
```

### Getting started


1) First run the  world simulator (https://github.com/yunjingliu96/world_simulator_exec)

2) Update world-service with WORLD_HOST & AMAZON_HOST with the corresponding host address.  

3) Run UPS applicaiton first by following below command. 

```
docker-compose build
docker-compose up -d
```

4) Once UPS servers are up run the Amazon applicaiton. 


## Contributions

This project was completed as part of an academic assignment with requirments provided requirments.pdf. Contributions were made solely by Koushik Annareddy Sreenath, Shravan MS, adhering to the project guidelines and requirements set by the course ECE-568 Engineering Robust Server Software 

## License

This project is an academic assignment and is subject to university guidelines on academic integrity and software use.

## Acknowledgments

- Thanks to Brian Rogers and the course staff for providing guidance and support throughout the project.
