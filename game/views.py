from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Quote, Player, Group, GridFlipLog
from django.http import JsonResponse
import random


def get_active_flips(request):
    data = GridFlipLog.objects.filter(is_status=True).values()
    return JsonResponse(list(data), safe=False)

@api_view(['GET'])
def get_quote_part(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET request required"}, status=405)

    diary_number = request.GET.get("diary_number")
    print("Received diary_number:", diary_number)

    if not diary_number:
        return JsonResponse({"error": "Missing diary_number"}, status=400)

    try:
        player = Player.objects.get(diary_id=diary_number)
    except Player.DoesNotExist:
        return JsonResponse({"error": "Player not found"}, status=404)

    part_text = player.quote.part_a if player.quote_part == "A" else player.quote.part_b

    return JsonResponse({
        "diary_number": diary_number,
        "quote_id": player.quote.id,
        "quote_part": player.quote_part,
    })
    
class DiaryEntryView(APIView):
    def post(self, request):
        diary_number = request.data.get("diary_number")
        group_name = request.data.get("group_name")

        if not diary_number:
            return Response({"error": "diary_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not group_name:
            return Response({"error": "group_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already registered
        if Player.objects.filter(diary_id=diary_number).exists():
            return Response({"error": "This diary number has already been registered."}, status=status.HTTP_400_BAD_REQUEST)

        # Get existing group (don't auto-create)
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            return Response({"error": "Group does not exist. Please check the group name."}, status=status.HTTP_400_BAD_REQUEST)

        # Choose a quote
        quotes = Quote.objects.all()
        if not quotes.exists():
            return Response({"error": "No quotes available."}, status=status.HTTP_404_NOT_FOUND)

        quote = quotes.first() if quotes.count() == 1 else random.choice(quotes)

        # Decide quote part (A or B)
        last_digit = int(diary_number[-1])
        part_type = "B" if last_digit % 2 == 0 else "A"
        part_text = quote.part_b if part_type == "B" else quote.part_a

        # Save player
        player = Player.objects.create(
            diary_id=diary_number,
            quote=quote,
            quote_part=part_type,
            has_registered=True,
            group=group
        )

        return Response({
            "diary_number": diary_number,
            "part": part_text,
            "part_type": part_type,
            "group": group.name
        }, status=status.HTTP_201_CREATED)


class VerifyQuotePairView(APIView):
    def post(self, request):
        diary_id_1 = request.data.get('diary_id_1')
        diary_id_2 = request.data.get('diary_id_2')

        if not diary_id_1 or not diary_id_2:
            return Response({"error": "Both diary IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            player1 = Player.objects.get(diary_id=diary_id_1)
            player2 = Player.objects.get(diary_id=diary_id_2)
        except Player.DoesNotExist:
            return Response({"error": "One or both diary IDs not found."}, status=status.HTTP_404_NOT_FOUND)

        # Identify which quote part each player has
        part_a = part_b = None
        if player1.quote_part == "A":
            part_a = player1.quote.part_a
        elif player1.quote_part == "B":
            part_b = player1.quote.part_b

        if player2.quote_part == "A":
            part_a = player2.quote.part_a if not part_a else part_a
        elif player2.quote_part == "B":
            part_b = player2.quote.part_b if not part_b else part_b

        if not part_a or not part_b:
            return Response({"error": "Match quote not found"}, status=status.HTTP_400_BAD_REQUEST)

        full_quote = part_a + " " + part_b

        try:
            matched_quote = Quote.objects.get(text=full_quote)
        except Quote.DoesNotExist:
            return Response({"error": "Combined quote does not match any known quote."}, status=status.HTTP_404_NOT_FOUND)

        available_flips = GridFlipLog.objects.filter(is_status=False)

        if not available_flips.exists():
            return Response({"error": "No available flip numbers remaining."}, status=status.HTTP_410_GONE)

        flip = random.choice(list(available_flips))
        flip.is_status = True
        flip.save()

        # Group points increment logic
        updated_groups = set()
        for player in [player1, player2]:
            if player.group and player.group.id not in updated_groups:
                group = player.group
                group.points += 1
                group.save()
                updated_groups.add(group.id)

        return Response({
            "flip_number": flip.flip_number,
            "quote": matched_quote.text,
            "message": "🎉 Congrats! You've flipped a grid."
        }, status=status.HTTP_200_OK)

class GroupPointsView(APIView):
    def get(self, request):
        groups = Group.objects.all().values("name", "points")
        return Response(list(groups), status=status.HTTP_200_OK)