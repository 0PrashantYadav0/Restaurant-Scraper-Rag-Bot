# Restaurant-Scraper-Rag-Bot

## Overview

This repository contains a web scraping and data processing project designed to collect restaurant data from various sources, construct a knowledge base using Retrieval-Augmented Generation (RAG), and provide a user-friendly interface for querying this data. The project utilizes Python, FastAPI for the backend, and React for the frontend.

## Features

-   **Web Scraping:** Collects data from specified restaurant sources.
-   **Knowledge Base Construction:** Processes scraped data and builds a vector store for efficient querying using RAG techniques.
-   **FastAPI Backend:** Serves the processed data and handles RAG-based queries via API endpoints, including WebSocket support for chat.
-   **React Frontend:** Provides an interactive user interface for asking questions, chatting with the bot (with session management), viewing restaurant details, and browsing menus.
-   **RAG Implementation:** Allows users to ask natural language questions about restaurants (general or specific), compare prices, check for dietary options (e.g., gluten-free), and more, leveraging the constructed knowledge base.
-   **Docker Support:** Includes Docker configuration for simplified setup and deployment.
-   **Data Processing & Storage:** Manages the storage and retrieval of restaurant information and menu items.
-   **Logging & Error Handling:** Implements basic logging and error management.
-   **Configuration Management:** Uses configuration files for managing settings.

## Live Demo and Functionality

### Deployed Application

Access the live application here: **[https://restaurant-scraper-rag-bot.onrender.com/](https://restaurant-scraper-rag-bot.onrender.com/)**

### Demo Video

[Demo Video](https://youtu.be/pDOFJSV_tNQ?si=QwroCY3DM35uH0lv) provides a walkthrough of the application, showcasing its features and functionality. (Please use headphones for a better experience.)

### Key Features Showcase

1.  **Ask General Questions:** Query the entire restaurant database. The RAG bot responds with relevant information based on the knowledge base. Compare prices, check dietary options, etc.
    ![Ask Questions](assets/ask-question.png)

2.  **General ChatBot:** Engage in a conversation with the chatbot using WebSockets and session management. The bot maintains context and answers based on the knowledge base.
    ![ChatBot](assets/chatbot.png)

3.  **Ask Specific Restaurant Questions:** Focus queries on a single restaurant.
    ![Ask Questions to one Restaurant only](assets/ask-question-id.png)

4.  **Specific Restaurant ChatBot:** Chat specifically about one restaurant, maintaining context via WebSockets.
    ![ChatBot to one Restaurant only](assets/chatbot-id.png)

5.  **View Menu:** Browse the menu of a specific restaurant with details and images.
    ![View menu](assets/view-menu.png)

6.  **View Restaurant Details:** Access comprehensive information about a specific restaurant (address, phone, website, etc.).
    ![View restaurant details](assets/restaurant-info.png)

## Setup Guide

[SETUP.md](SETUP.md) provides a detailed setup guide for running the project locally, including instructions for installing dependencies, configuring the environment, and launching the application.

## Architecture

[ARCHITECTURE.md](ARCHITECTURE.md) provides an overview of the system architecture, detailing the data flow, components (scraper, backend, frontend, knowledge base), and their interactions.

## Contributing

Contributions are welcome! Please follow standard GitHub practices: open an issue to discuss changes or submit a pull request with your improvements. Adhere to the project's coding standards and guidelines.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project was inspired by the need for a comprehensive tool for restaurant data scraping, analysis, and querying using modern AI techniques. Thanks to the open-source community.

## Contact

For inquiries or feedback, contact the project maintainer via their website: [prashantyadav.site](https://prashantyadav.site).

## Author

-   **Prashant Yadav**
    -   GitHub: [0PrashantYadav0](https://github.com/0PrashantYadav0)
    -   LinkedIn: [prashantyadav097](https://www.linkedin.com/in/prashantyadav097/)
