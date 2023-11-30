import json
from PIL import Image, ImageDraw

def annotate(json_path, suffix):
    """
    :param json_path: annotation path with the annotations and paths for the images
    :suffix: just a suffix for the annotated picture file
    :return: Nothing, for each image, it will create a new annotated image with the boxes drawn.
    """

    with open(json_path, 'r') as file:
        json_data = json.load(file)

    colors = {
        'single_axle': 'green',
        'grouped_axles': 'purple',
        'car': 'red',
        'other': 'grey'
    }
    for data_image in json_data['images']:
        image = Image.open(data_image['location'])
        width, height = image.size
        draw = ImageDraw.Draw(image)
        for annotation in data_image['annotated_regions']:
            if annotation['region_type'] == 'Box':
                col = colors[annotation['tags'][0]]
                x_min = float(annotation['region']['xmin']) * width
                x_max = float(annotation['region']['xmax']) * width
                y_min = float(annotation['region']['ymin']) * height
                y_max = float(annotation['region']['ymax']) * height
                xmin = min(x_min, x_max)
                xmax = max(x_min, x_max)
                ymin = min(y_min, y_max)
                ymax = max(y_min, y_max)
                draw.rectangle((xmin, ymin, xmax, ymax), outline=col, width=2)
        new_img_path = data_image['location'].replace('.jpg', '')
        new_img_path += '_annotated_'+suffix+'.jpg'
        image.save(new_img_path)