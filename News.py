import sys
import asyncio
import threading
from datetime import datetime
import feedparser
import html2text
import aiohttp
from io import BytesIO
from PIL import Image, ImageTk
import webbrowser
import tkinter as tk
from tkinter import ttk
from googletrans import Translator

class NewsApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("News Aggregator")
        self.geometry("1000x600")

        self.is_dark_mode = False

        self.title_label = tk.Label(self, text="Daily News Journal", font=("Times New Roman", 28, "bold"), bg="lightblue", fg="darkblue")
        self.title_label.pack(pady=10)

        self.date_label = tk.Label(self, text=datetime.now().strftime("%A, %B %d, %Y"), font=("Times New Roman", 18), bg="lightblue", fg="darkblue")
        self.date_label.pack(pady=5)

        self.search_frame = tk.Frame(self, bg="lightblue")
        self.search_frame.pack(pady=5)

        self.search_label = tk.Label(self.search_frame, text="Search:", font=("Times New Roman", 18), bg="lightblue", fg="darkblue")
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = tk.Entry(self.search_frame, font=("Times New Roman", 18), bg="white", fg="black")
        self.search_entry.pack(side=tk.LEFT, padx=5)

        self.search_button = tk.Button(self.search_frame, text="Search", command=self.search_news, bg="darkblue", fg="white")
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.fetch_button = tk.Button(self, text="Fetch News", font=("Times New Roman", 12), command=self.start_fetching_news, bg="darkblue", fg="white")
        self.fetch_button.pack(pady=5)

        self.language_var = tk.StringVar(self)
        self.language_var.set("en")  # Default language is English
        self.language_menu = tk.OptionMenu(self, self.language_var, "en", "es", "fr", "de", "zh-cn", "ja", "ru", "ar")
        self.language_menu.config(bg="lightblue", fg="darkblue")
        self.language_menu.pack(pady=5)

        self.news_area = tk.Canvas(self, bg="white")
        self.news_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.news_area.yview, bg="lightblue")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.news_area.configure(yscrollcommand=self.scrollbar.set)

        self.news_frame = tk.Frame(self.news_area, bg="white")
        self.news_area.create_window((0, 0), window=self.news_frame, anchor="nw")

        self.news_frame.bind("<Configure>", lambda e: self.news_area.configure(scrollregion=self.news_area.bbox("all")))

        self.loading_label = tk.Label(self, text="", font=("Times New Roman",), bg="lightblue", fg="darkblue")
        self.loading_label.pack(pady=5)

        self.progress = ttk.Progressbar(self, orient="horizontal", length=100, mode="determinate")
        self.progress.pack(pady=5)

        self.dark_mode_button = tk.Button(self, text="Toggle Dark Mode", command=self.toggle_dark_mode, bg="darkblue", fg="white")
        self.dark_mode_button.pack(pady=5)

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()

        self.images = []  # To keep references to images
        self.articles = []  # To store fetched articles
        self.translator = Translator()

    def start_fetching_news(self):
        self.loading_label.config(text="Fetching news, please wait...")
        self.progress["value"] = 0
        self.task = asyncio.run_coroutine_threadsafe(self.fetch_news(), self.loop)
        self.check_task()

    async def fetch_news(self):
        for widget in self.news_frame.winfo_children():
            widget.destroy()
        self.articles.clear()

        news_feeds = [
            "http://feeds.bbci.co.uk/news/rss.xml",
            "http://rss.cnn.com/rss/edition_world.rss",
            "http://feeds.reuters.com/Reuters/worldNews",
            "https://www.theguardian.com/international/rss",
            "https://www.aljazeera.com/xml/rss/all.xml",
            "https://techcrunch.com/feed/"  # Technology news feed
        ]

        tasks = [self.fetch_from_feed(feed) for feed in news_feeds]
        await asyncio.gather(*tasks)

    async def fetch_from_feed(self, feed):
        self.add_label_to_news_area(f"Fetching news from {feed}\n\n")
        try:
            d = feedparser.parse(feed)
            print(f"Parsed feed: {feed}")  # Debugging line
            for entry in d.entries[:5]:
                article = {
                    "title": entry.title,
                    "description": html2text.html2text(entry.description),
                    "link": entry.link,
                    "media_content": entry.media_content if 'media_content' in entry else None
                }
                self.articles.append(article)
                await self.display_article(article)
                self.progress["value"] += 20  # Update progress bar
        except Exception as e:
            self.add_label_to_news_area(f"Error fetching news from {feed}: {e}\n")
            print(f"Error fetching news from {feed}: {e}")  # Debugging line
        self.add_label_to_news_area("\n")

    async def display_article(self, article):
        target_language = self.language_var.get()
        translated_title = self.translator.translate(article["title"], dest=target_language).text
        translated_description = self.translator.translate(article["description"], dest=target_language).text

        self.add_label_to_news_area(translated_title + "\n")
        self.add_label_to_news_area(translated_description + "\n\n")
        if article["media_content"]:
            for media in article["media_content"]:
                if 'url' in media:
                    image_url = media['url']
                    asyncio.run_coroutine_threadsafe(self.fetch_and_display_image(image_url), self.loop)

    async def fetch_and_display_image(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    image_data = await response.read()
                    image = Image.open(BytesIO(image_data))
                    image.thumbnail((500, 500))  # Resize image to fit in the text widget
                    tk_image = ImageTk.PhotoImage(image)

                    self.add_image_to_news_area(tk_image)
        except Exception as e:
            self.add_label_to_news_area(f"Error loading image: {e}\n")

    def add_label_to_news_area(self, text):
        label = tk.Label(self.news_frame, text=text, anchor="w", justify="left", font=("Times New Roman", 14), bg="white", fg="black")
        label.pack(fill=tk.X, padx=10, pady=2)

    def add_image_to_news_area(self, tk_image):
        label = tk.Label(self.news_frame, image=tk_image, bg="white")
        label.pack(padx=10, pady=2)
        self.images.append(tk_image)  # Keep a reference to avoid garbage collection

    def open_link(self, url):
        webbrowser.open(url)

    def search_news(self):
        search_term = self.search_entry.get().lower()
        for widget in self.news_frame.winfo_children():
            widget.destroy()
        for article in self.articles:
            if search_term in article["title"].lower() or search_term in article["description"].lower():
                asyncio.run_coroutine_threadsafe(self.display_article(article), self.loop)

    def check_task(self):
        if self.task.done():
            self.loading_label.config(text="")
            try:
                self.task.result()
            except Exception as e:
                self.add_label_to_news_area(f"An error occurred: {e}\n")
        else:
            self.after(100, self.check_task)

    def toggle_dark_mode(self):
        if self.is_dark_mode:
            self.configure(bg="white")
            self.title_label.config(bg="lightblue", fg="darkblue")
            self.date_label.config(bg="lightblue", fg="darkblue")
            self.search_frame.config(bg="lightblue")
            self.search_label.config(bg="lightblue", fg="darkblue")
            self.search_entry.config(bg="white", fg="black")
            self.search_button.config(bg="darkblue", fg="white")
            self.fetch_button.config(bg="darkblue", fg="white")
            self.loading_label.config(bg="lightblue", fg="darkblue")
            self.dark_mode_button.config(bg="darkblue", fg="white")
            self.news_frame.config(bg="white")
        else:
            self.configure(bg="black")
            self.title_label.config(bg="black", fg="white")
            self.date_label.config(bg="black", fg="white")
            self.search_frame.config(bg="black")
            self.search_label.config(bg="black", fg="white")
            self.search_entry.config(bg="black", fg="white")
            self.search_button.config(bg="black", fg="white")
            self.fetch_button.config(bg="black", fg="white")
            self.loading_label.config(bg="black", fg="white")
            self.dark_mode_button.config(bg="black", fg="white")
            self.news_frame.config(bg="black")
        self.is_dark_mode = not self.is_dark_mode

if __name__ == "__main__":
    app = NewsApp()
    app.mainloop()