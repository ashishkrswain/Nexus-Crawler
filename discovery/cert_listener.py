import certstream
import threading
import queue

class CertStreamDiscoverer:
    def __init__(self):
        self.domain_queue = queue.Queue()
        self.is_running = False

    def _callback(self, message, context):
        if message['message_type'] == "certificate_update":
            all_domains = message['data']['leaf_cert']['all_domains']
            for domain in all_domains:
                if not domain.startswith('*') and len(domain) < 40:
                    self.domain_queue.put(domain)

    def _start(self):
        print("[Discovery] Connecting to CertStream...")
        certstream.listen_for_events(self._callback, url='wss://certstream.calidog.io/')

    def start_background(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._start, daemon=True)
        self.thread.start()
        print("[Discovery] CertStream thread started.")

    def get_domains(self, max_batch=50):
        """Pulls a batch of newly discovered domains from the queue."""
        domains = []
        while not self.domain_queue.empty() and len(domains) < max_batch:
            try:
                domains.append(self.domain_queue.get_nowait())
            except queue.Empty:
                break
        # Deduplicate
        return list(set(domains))
