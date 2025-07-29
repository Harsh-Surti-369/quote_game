from .models import Quote, Diary, Match, GridFlipLog, Player, Group
from rest_framework import serializers


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ['id', 'text', 'part_a', 'part_b']

class DiarySerializer(serializers.ModelSerializer):
    quote = QuoteSerializer(read_only = True)
    
    class Meta:
        model = Diary
        fields = ['id', 'diary_number', 'quote', 'part_type']

class MatchSerializer(serializers.ModelSerializer):
    diary_1 = DiarySerializer(read_only=True)
    diary_2 = DiarySerializer(read_only=True)
    quote = QuoteSerializer(read_only=True)
    
    class Meta:
        model = Match
        fields = ['id', 'diary_1', 'diary_2', 'quote', 'created_at']

class GridFlipLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridFlipLog
        fields = ['id', 'flip_number', 'flipped_at']

class PlayerSerializer(serializers.ModelSerializer):
    group = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Group.objects.all()
    )

    class Meta:
        model = Player
        fields = ['id', 'diary_id', 'quote', 'quote_part', 'has_registered', 'group']

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']