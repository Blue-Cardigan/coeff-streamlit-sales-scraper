from joblib import Memory
import os

# Define a persistent cache location
CACHE_DIR = ".cache_joblib"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

memory = Memory(CACHE_DIR, verbose=0) # verbose=1 for debugging cache misses/hits

# You can create specific cachers if needed, or use the general 'memory' instance.
# For example, one for scraping and one for LLM calls if they need different settings.
scrape_memory = Memory(os.path.join(CACHE_DIR, 'scraping'), verbose=0)
llm_memory = Memory(os.path.join(CACHE_DIR, 'llm'), verbose=0)

# To clear cache (e.g., for development or if underlying functions change significantly):
# memory.clear()
# scrape_memory.clear()
# llm_memory.clear() 