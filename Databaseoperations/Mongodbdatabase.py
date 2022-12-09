import pymongo



client = pymongo.MongoClient("mongodb://mongodb:mongodb@ac-rdwzeeq-shard-00-00.ffsxijb.mongodb.net:27017,ac-rdwzeeq-shard-00-01.ffsxijb.mongodb.net:27017,ac-rdwzeeq-shard-00-02.ffsxijb.mongodb.net:27017/?ssl=true&replicaSet=atlas-1n8oe5-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client.test
