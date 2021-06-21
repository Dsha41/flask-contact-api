"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for, json
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, Contact, Group, RelationContactGroup
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/user', methods=['GET'])
def handle_hello():

    response_body = {
        "msg": "Hello, this is your GET /user response "
    }

    return jsonify(response_body), 200

@app.route('/contact/all', methods=['GET'])
def get_all_contacts():
    '''
        Get all the contacts form the database
    '''

    all_contacts = Contact.query.all()

    return jsonify([x.serialize() for x in all_contacts]), 200

@app.route('/contact', methods=['POST'])
def create_contact():
    '''
        Creates a contact from the data of the request,
        the email must be unique, if not returns a 400
        after the contact is create its create the relation with the groups
    '''
    data = json.loads(request.data)
    # Creating the contact
    new_contact = Contact(
        full_name=data["full_name"],
        email=data["email"],
        address=data["address"],
        phone=data["phone"],
    )

    db.session.add(new_contact)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({"msg": "Email must be unique"}), 400

    # Creating the relation
    for group_id in data["groups"]:
        relation = RelationContactGroup(contact_id=new_contact.id, group_id=group_id)
        db.session.add(relation)
        db.session.commit()
        return jsonify(new_contact.serialize()), 200

@app.route('/contact/<int:contact_id>', methods=['GET', 'PUT', 'DELETE'])
def process_contact(contact_id):
    '''
        GET: Gets a contact by its id
        PUT: Modifies a contact by its id. For now it does not modify the groups
        DELETE: Deletes a contact by its id 
    '''

    contact = Contact.query.get(contact_id)

    if contact == None:
        return jsonify({"msg": "Contact not found"}), 404

    if request.method == 'GET':
        return jsonify(contact.serialize()), 200
    elif request.method == 'PUT':
        try: 
            data = json.loads(request.data)
            if 'full_name' in data:
                contact.full_name = data['full_name']
            if 'email' in data:
                contact.email = data['email']
            if 'address' in data: 
                contact.address = data['address']
            if 'phone' in data:
                contact.phone = data['phone']
        except:
            raise APIException('Some data failed', status_code=400)
        db.session.add(contact)
        try:
            db.session.commit()
        except:
            db.session.rollback()
        return jsonify(contact.serialize()), 200


    elif request.method == 'DELETE':
        db.session.delete(contact)
        try:
            db.session.commit()
        except:
            db.session.rollback()
        print(contact)
        return jsonify({"deleted": {
            "id": contact.id,
            "full_name": contact.full_name
        }}), 200


@app.route('/group', methods=['GET'])
def get_all_groups():
    '''
        Gets all the groups of the database 
    '''

    groups = Group.query.all()
    return jsonify([group.serialize() for group in groups]), 200


@app.route('/group', methods=['POST'])
def create_group():
    '''
        Creates a group and then makes the relationship between that
        group and all the contacts ids listed
    '''
    # Creating the group
    data = json.loads(request.data)
    group = Group(
        name=data["name"]
    )

    db.session.add(group)
    try: 
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({"msg": "Error creating the group"}), 400

    # Creating the relations
    for contact_id in data["contacts"]:
        relation = RelationContactGroup(contact_id=contact_id, group_id=group.id)
        db.session.add(relation)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            print("Error creating the relations")

@app.route('/group/<int:group_id>', methods=['GET', 'PUT', 'DELETE'])
def process_group(group_id):
    '''
        GET: Gets a group by its id
        PUT: Modifies a group by its id. Only the name
        DELETE: Deletes a group by its id 
    '''
    group = Group.query.get(group_id)

    if group == None:
        return jsonify({"msg": "Group not found"}), 404

    if request.method == 'GET':
        return jsonify(group.serialize()), 200
    elif request.method == 'PUT':
        try: 
            data = json.loads(request.data)
            if 'name' in data:
                group.name = data['name']
        except:
            raise APIException('Some data failed', status_code=400)
        db.session.add(group)
        try:
            db.session.commit()
        except:
            db.session.rollback()
        return jsonify(group.serialize()), 200

    elif request.method == 'DELETE':
        db.session.delete(group)
        db.session.commit()
        return jsonify({"deleted": {
            "id": group.id,
            "name": group.name
        }}), 200
    

    return jsonify(group.serialize()), 200

# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
