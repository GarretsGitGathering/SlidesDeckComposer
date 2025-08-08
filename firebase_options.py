import firebase_admin
from firebase_admin import credentials, firestore
from slidesOps import get_slides

# Initialize Firebase Admin SDK
cred = credentials.Certificate("slidesdatabase-c12eb-firebase-adminsdk-id40o-48ad49b096.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://slidesdatabase-c12eb-default-rtdb.firebaseio.com/'
})

# Reference to the database
db = firestore.client()

def get_presentation_ids(doc_type):
    try:
        doc_ref = db.collection('presentations').document(doc_type)
        doc = doc_ref.get()
        if doc.exists:
            # Get all fields from the document
            presentations = doc.to_dict()
            # Extract the keys which represent the presentation IDs
            presentation_ids = list(presentations.values())
            print(f'Presentation IDs for {doc_type}:', presentation_ids)
            return presentation_ids
        else:
            print('No such document!')
            return []
    except Exception as e:
        print(f'Error getting document: {e}')
        return []

# Function to update an existing document or create it if it doesn't exist
def update_document(collection_name, document_id, field_name, field_value, field_path=False):
    try:
        # Get Firestore client
        db = firestore.client()

        # Reference to the specific document
        doc_ref = db.collection(collection_name).document(document_id)

        # Check if we are using a field path
        if field_path:
            update_data = {db.field_path(field_name): field_value}
        else:
            update_data = {field_name: field_value}

        # Use set with merge=True to create or update the document
        doc_ref.set(update_data, merge=True)

        print(f"Document {document_id} in collection {collection_name} successfully updated/created with {field_name}: {field_value}")

    except Exception as e:
        print(f"An error occurred: {e}")


def get_slides_by_category(collection_name, category):
    # Fetch slides in the given category
    slides_collection = db.collection(collection_name)
    slides = slides_collection.stream()

    matching_slides = []

    for slide in slides:
        slide_data = slide.to_dict()
        slide_category = slide_data['category']

        if(slide_category == category):
            matching_slides.append(slide_data)
        else:
            continue

    return matching_slides


# find the slide by the objectId
def find_slide(objectId):
    slides_collection = db.collection("categorized_slides")
    slides = slides_collection.stream()

    for slide in slides:
        if(slide["objectId"] == objectId):  return slide
    
    return {"error": "could not find the slide"}

# # Example usage
# presentation_ids = get_presentation_ids('formal')
# for presentation_id in presentation_ids:
#     print(presentation_id)

#     print(get_slides(presentation_id))