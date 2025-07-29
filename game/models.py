from django.db import models

# Create your models here.

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    points = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Quote(models.Model):
    text = models.TextField()
    part_a = models.CharField(max_length=255)
    part_b = models.CharField(max_length=255)

    def __str__(self):
        return f"Quote #{self.id}: {self.text[:50]}"

class Diary(models.Model):
    PART_CHOICES = (
        ('A', 'Part A'),
        ('B', 'Part B'),
    )
    
    diary_number = models.CharField(max_length=20,unique=True)
    quote = models.ForeignKey(Quote,on_delete=models.CASCADE)
    part_type = models.CharField(max_length=1,choices=PART_CHOICES)
    
    def ___str__(self):
        return f"Diary {self.diary_number} ({self.part_type})"

class Match(models.Model):
    diary_1 = models.ForeignKey(Diary,on_delete=models.CASCADE,related_name="match_diary_1")
    diary_2 = models.ForeignKey(Diary,on_delete=models.CASCADE,related_name="match_diary_2")
    quote = models.ForeignKey(Quote,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Match: {self.diary_1.diary_number} + {self.diary_2.diary_number} - Quote #{self.quote.id}"


class GridFlipLog(models.Model):
    flip_number = models.PositiveIntegerField()
    is_status = models.BooleanField(default=False)
    flipped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Flip #{self.flip_number} at {self.flipped_at.strftime('%Y-%m-%d %H:%M:%S')}"


class Player(models.Model):
    diary_id = models.CharField(max_length=20, unique=True)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    quote_part = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B")])
    has_registered = models.BooleanField(default=False)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
  
    def __str__(self):
        return f"{self.diary_id} -> Quote {self.quote.id} - Part {self.quote_part}"
    
    
# DB model only for frontend
# models_frontend.py
class FrontendQuotePair(models.Model):
    diary_number = models.CharField(max_length=20)
    quote_id = models.IntegerField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'your_frontend_table_name'