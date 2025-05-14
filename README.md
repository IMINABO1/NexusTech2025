# Louisiana Deals Platform (NexusTech2025)

A modern web platform for buying, selling, and exchanging items within Louisiana communities. Built with Flask and modern web technologies.

## Features

- 🛍️ **Deal Management**
  - Create, edit, and manage deals
  - Support for sales and free items
  - Image upload capabilities
  - Location-based listings

- 💰 **Payment Processing**
  - Secure payment processing
  - Transaction history
  - Database-backed transaction records

- 👤 **User Management**
  - User profiles with avatars
  - Authentication system
  - Rating system

- 💬 **Communication**
  - Built-in chat system
  - Real-time messaging
  - Deal-specific conversations

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- SQLite3

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd NexusTech2025
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python init_db.py
```

5. Start the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
NexusTech2025/
├── app.py              # Main application file with routes and models
├── init_db.py         # Database initialization script
├── requirements.txt   # Python dependencies
├── static/           # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── uploads/
└── templates/        # HTML templates
    ├── base.html
    ├── deals.html
    ├── login.html
    └── ...
```

## Environment Variables

The following environment variables should be set:

- `SECRET_KEY` - Flask secret key for session security
- `SQLALCHEMY_DATABASE_URI` - Database connection string (defaults to SQLite)

## Contributing

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Testing

To run the tests:
```bash
python -m pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository.

## Authors

- Initial development team at NexusTech2025
- Contributors welcome!