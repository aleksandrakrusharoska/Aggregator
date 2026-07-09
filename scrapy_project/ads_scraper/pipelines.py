import json


class JsonWriterPipeline:
    """Write items to a JSON Lines file named <spider.name>_items.jl"""

    def open_spider(self, spider):
        self.file = open(f"{spider.name}_items.jl", "w", encoding="utf-8")

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item
