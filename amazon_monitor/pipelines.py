import mysql.connector


class AmazonPipeline:

    def open_spider(self, spider):

        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Kumar@123",
            database="amazon_prices",
        )

        self.cursor = self.conn.cursor()

    def process_item(self, item, spider):

        sql = """
        INSERT INTO price_history (asin, seller, price)
        VALUES (%s, %s, %s)
        """

        values = (item.get("asin"), item.get("seller"), item.get("price"))

        self.cursor.execute(sql, values)

        self.conn.commit()

        return item
