web: gunicorn app:app
web: python app_dashboard.py
```

Wait, that's not correct. The instruction says to use Gunicorn if it's installed, otherwise use `python app_dashboard.py`. So, the correct edit would be to replace the existing line with a conditional statement. However, Procfile doesn't support conditional statements. 

A possible solution would be to use a single line that checks if Gunicorn is installed, and if not, falls back to `python app_dashboard.py`. Here's an example:

```
web: gunicorn app:app || python app_dashboard.py
