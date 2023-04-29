# erss-project-ka266-sm952

# Mini-Amazon / Mini-UPS project for ECE568 project
We have developed Mini-UPS following the requirements of  https://sakai.duke.edu/access/content/attachment/f74215cd-4881-4c67-a401-0f9ed2057e60/Assignments/f39cee26-6d09-40ce-8566-a0d3f2b04c65/Project%20Spec%20v2.pdf

#Authors 

Koushik Annareddy Sreenath (ka266)
Shravan Mysore Seethraman (sm952)

## Getting started


First run the  world simulator (https://github.com/yunjingliu96/world_simulator_exec)
Update world-service with WORLD_HOST & AMAZON_HOST with the corresponding host address.  
Run UPS applicaiton first by following below command. 

```
docker-compose build
docker-compose up -d
```

Once UPS servers are up run the Amazon applicaiton. 
