# E-Commerce Platform

A full-featured Django e-commerce platform with multi-vendor support, product variations, and comprehensive admin controls.

## 🚀 Features

### 🛍️ **Shopping Experience**
- Browse products by categories
- Advanced search with smart keyword matching
- Product variations (Color, Size, Storage, etc.)
- Interactive image galleries with zoom
- Shopping cart with session persistence
- User reviews and ratings
- Related products suggestions

### 👥 **User Management**
- User registration and authentication
- Profile management with avatars
- Order history tracking
- Password change functionality
- Seller application system

### 🏪 **Multi-Vendor Support**
- Seller registration and approval workflow
- Individual seller stores/profiles
- Product management for sellers
- Seller verification badges
- Business profile management

### 📦 **Product Management**
- Rich product details with specifications
- Multiple product images
- Product variations with individual:
  - Stock quantities
  - Price adjustments
  - Variation-specific images
  - SKU management
- Category-based organization
- Admin approval system

### 🔧 **Admin Features**
- Product approval/rejection workflow
- Seller management and verification
- Category management
- Variation type configuration
- User profile administration
- Order management system

### 🎨 **Product Variations**
- **Color variations** with color swatches
- **Size variations** with button selection
- **Storage/Capacity** options
- **Custom variation types**
- Variation-specific pricing and stock
- Multiple images per variation

## 🛠️ **Tech Stack**

- **Backend:** Django 5.2.4
- **Database:** SQLite (development) / PostgreSQL (production ready)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
- **Image Handling:** Pillow
- **Authentication:** Django built-in auth system

## 📋 **Prerequisites**

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

## ⚡ **Quick Setup**

### 1. Clone the Repository
```bash
git clone https://github.com/ChakuHo/DjangoWebapp
cd DjangoWebapp
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## 📁 **Project Structure**

```
ecommerce-platform/
├── products/           # Product management app
├── users/             # User authentication & profiles
├── cart/              # Shopping cart functionality
├── orders/            # Order management
├── master/            # Base templates and static files
├── static/            # CSS, JS, images
├── media/             # User uploaded files
├── templates/         # HTML templates
└── manage.py
```

## 🏗️ **Key Models**

### Products App
- `Product` - Main product information
- `Category` - Product categorization
- `ProductVariation` - Product variants (color, size, etc.)
- `VariationType` - Types of variations available
- `VariationOption` - Specific options for each variation type
- `Review` - Customer reviews and ratings

### Users App
- `Profile` - Extended user information
- Seller management fields
- Business profile data

## 🎯 **Usage Guide**

### For Customers:
1. **Browse Products:** Navigate categories or use search
2. **Product Details:** View variations, images, and reviews
3. **Add to Cart:** Select variations and add to cart
4. **Checkout:** Complete purchase process
5. **Review:** Leave reviews for purchased products

### For Sellers:
1. **Apply:** Submit seller application
2. **Get Approved:** Wait for admin approval
3. **Add Products:** Create products with variations
4. **Manage Inventory:** Update stock and pricing
5. **View Orders:** Track received orders

### For Admins:
1. **Approve Sellers:** Review and approve seller applications
2. **Manage Products:** Approve/reject product submissions
3. **Configure Categories:** Set up product categories
4. **Variation Types:** Configure available variation types
5. **User Management:** Manage user accounts and permissions

## 🚀 **Deployment**

### Environment Variables
Create a `.env` file:
```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=your-database-url
```

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure proper database (PostgreSQL recommended)
- [ ] Set up media file serving (AWS S3 or similar)
- [ ] Configure email backend
- [ ] Set up HTTPS
- [ ] Configure static files serving

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🐛 **Common Issues**

### Migration Issues
```bash
python manage.py makemigrations --empty appname
python manage.py migrate --fake-initial
```

### Static Files Not Loading
```bash
python manage.py collectstatic
```

### Permission Errors
- Ensure proper file permissions for media directory
- Check database write permissions

## 📝 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 **Support**

- Create an [Issue](https://github.com/ChakuHo/DjangoWebapp/issues) for bug reports
- [Discussions](https://github.com/ChakuHo/DjangoWebapp/discussions) for questions
- Email: bigyan12341@gmail.com

## 🙏 **Acknowledgments**

- Django community for the amazing framework
- Bootstrap for responsive design components
- Contributors and testers

---

⭐ **Star this repository if you found it helpful!**

---

**Made with ❤️ using Django**