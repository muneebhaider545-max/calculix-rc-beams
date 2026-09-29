from PIL import Image
p='publication_figures/Fig_H_Combined_OpenRadioss_Plate.png'
im=Image.open(p).convert('RGB')
im.thumbnail((1800,1800))
im.save('publication_figures/OpenRadioss_Publication_Preview.jpg',quality=88,optimize=True)
print('WROTE publication_figures/OpenRadioss_Publication_Preview.jpg')
