--- a/test_db_connector.py
@@ -10,6 +10,25 @@
 def test_connect_success(self):
     # Your existing test case for successful connection
 
+def test_connect_failure_fallback(self):
+    with patch('db_connector.MyDBConnector._connect') as mock_connect:
+        mock_connect.side_effect = [ConnectionError, ConnectionError, None]
+        db_connector = MyDBConnector()
+        result = db_connector.connect()
+        self.assertIsNone(result)
+
+@patch('time.sleep')
+def test_connect_failure_timeout(self, mock_sleep):
+    with patch('db_connector.MyDBConnector._connect') as mock_connect:
+        mock_connect.side_effect = [ConnectionError] * 10
+        db_connector = MyDBConnector()
+        with self.assertRaises(TimeoutException):
+            db_connector.connect(timeout=5)
+
+@patch('time.sleep')
+def test_connect_success_with_delay(self, mock_sleep):
+    with patch('db_connector.MyDBConnector._connect') as mock_connect:
+        mock_connect.side_effect = [ConnectionError, ConnectionError, None]
+        db_connector = MyDBConnector()
+        result = db_connector.connect(delay=2)
+        self.assertIsNone(result)
+
 class TestMyDBCursor(unittest.TestCase):
     # Your existing test cases for the cursor class
