from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Quote, Player, Group, GridFlipLog
from django.http import JsonResponse
from django.db import transaction, connections
from django.db.models import Q, F
import random


def get_active_flips(request):
    data = GridFlipLog.objects.filter(is_status=True).values()
    return JsonResponse(list(data), safe=False)
 
@api_view(['GET'])
def get_quote_part(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET request required"}, status=405)

    diary_number = request.GET.get("diary_number")

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
        "quote_text": player.quote.text,
        "quote_part": player.quote_part,
        "part_text": part_text,  
        "part_a": player.quote.part_a,
        "part_b": player.quote.part_b
    })

class DiaryEntryView(APIView):
    def post(self, request):
        diary_number = request.data.get("diary_number")
        group_name = request.data.get("group_name")

        if not diary_number:
            return Response({"error": "diary_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not group_name:
            return Response({"error": "group_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try to fetch group first
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            return Response({"error": "Group does not exist. Please check the group name."}, status=status.HTTP_400_BAD_REQUEST)

        # If player already registered, return the existing data
        existing_player = Player.objects.select_related('quote', 'group').filter(diary_id=diary_number).first()
        if existing_player:
            part_text = (
                existing_player.quote.part_b if existing_player.quote_part == "B" 
                else existing_player.quote.part_a
            )
            return Response({
                "diary_number": diary_number,
                "part": part_text,
                "quote": existing_player.quote.text,
                "part_type": existing_player.quote_part,
                "group": existing_player.group.name
            }, status=status.HTTP_200_OK)

        # Get available quotes
        quotes = list(Quote.objects.all())
        if not quotes:
            return Response({"error": "No quotes available."}, status=status.HTTP_404_NOT_FOUND)

        quote = random.choice(quotes)

        # Determine part type
        last_digit = int(diary_number[-1]) if diary_number[-1].isdigit() else random.randint(0, 9)
        part_type = "B" if last_digit % 2 == 0 else "A"
        part_text = quote.part_b if part_type == "B" else quote.part_a

        # Create new player
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
            "quote": quote.text,
            "part_type": part_type,
            "group": group.name
        }, status=status.HTTP_201_CREATED)
        

class VerifyQuotePairView(APIView):

    def post(self, request):
        diary_id_1 = request.data.get("diary_id_1")
        diary_id_2 = request.data.get("diary_id_2")

        if not diary_id_1 or not diary_id_2:
            return Response({"error": "Both diary IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent self-pairing
        if diary_id_1 == diary_id_2:
            return Response({"error": "Cannot pair a player with themselves."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            player1 = Player.objects.get(diary_id=diary_id_1)
            player2 = Player.objects.get(diary_id=diary_id_2)
        except Player.DoesNotExist:
            return Response({"error": "One or both players not found."}, status=status.HTTP_404_NOT_FOUND)

        print(f"Player 1: {player1.diary_id}")
        print(f"Player 2: {player2.diary_id}")
        
             # Check if already paired
        existing_flip = GridFlipLog.objects.filter(
            Q(player1=player1) | Q(player2=player1) |
            Q(player1=player2) | Q(player2=player2),
            is_status=True
        ).first()

        if existing_flip:
            if (existing_flip.player1 == player1 and existing_flip.player2 == player2) or \
               (existing_flip.player1 == player2 and existing_flip.player2 == player1):
                return Response({
                    "flip_number": existing_flip.flip_number,
                    "message": "You are already paired together.",
                    "paired_with": player2.diary_id if existing_flip.player1 == player1 else player1.diary_id
                }, status=status.HTTP_200_OK)

            if existing_flip.player1 == player1 or existing_flip.player2 == player1:
                paired_with = existing_flip.player2 if existing_flip.player1 == player1 else existing_flip.player1
                return Response({
                    "error": f"You are already paired with {paired_with.diary_id}.",
                    "flip_number": existing_flip.flip_number
                }, status=status.HTTP_409_CONFLICT)
            else:
                paired_with = existing_flip.player2 if existing_flip.player1 == player2 else existing_flip.player1
                return Response({
                    "error": f"{player2.diary_id} is already paired with {paired_with.diary_id}.",
                    "flip_number": existing_flip.flip_number
                }, status=status.HTTP_409_CONFLICT)

        # Assign a new flip
        available_flip = GridFlipLog.objects.filter(is_status=False).first()
        print(available_flip)
        if not available_flip:
            return Response({"error": "No available flip numbers."}, status=status.HTTP_410_GONE)

        available_flip.player1 = player1.diary_id
        available_flip.player2 = player2.diary_id
        available_flip.is_status = True
        available_flip.save()


        flip_number = available_flip.flip_number

        # Update default DB
        available_flip.player1 = player1
        available_flip.player2 = player2
        available_flip.is_status = True
        print(available_flip)
        group1 = player1.group
        group2 = player2.group

        if group1 and group2:
            if group1 == group2:
                group1.points += 2
                group1.save(using='default')
            else:
                group1.points += 1
                group2.points += 1
                group1.save(using='default')
                group2.save(using='default')

        # # Update same flip_number in lap1end DB
        # try:
        #     flip_lap1end = GridFlipLog.objects.using('lap1end').get(flip_number=flip_number)
        #     flip_lap1end.player1 = player1
        #     flip_lap1end.player2 = player2
        #     flip_lap1end.is_status = True
        #     flip_lap1end.save(using='lap1end')
        # except GridFlipLog.DoesNotExist:
        #     return Response({"error": "Flip not found in lap1end DB."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Pairing successful.",
            "flip_number": available_flip.flip_number,
            "paired": [player1.diary_id, player2.diary_id]
        }, status=status.HTTP_201_CREATED)



# class VerifyQuotePairView(APIView):
#     def post(self, request):
#         diary_id_1 = request.data.get('diary_id_1')
#         diary_id_2 = request.data.get('diary_id_2')

#         if not diary_id_1 or not diary_id_2:
#             return Response({"error": "Both diary IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             player1 = Player.objects.get(diary_id=diary_id_1)
#             player2 = Player.objects.get(diary_id=diary_id_2)
#         except Player.DoesNotExist:
#             return Response({"error": "One or both diary IDs not found."}, status=status.HTTP_404_NOT_FOUND)

#         # Match quote parts
#         part_a = part_b = None
#         if player1.quote_part == "A":
#             part_a = player1.quote.part_a
#         elif player1.quote_part == "B":
#             part_b = player1.quote.part_b

#         if player2.quote_part == "A" and not part_a:
#             part_a = player2.quote.part_a
#         elif player2.quote_part == "B" and not part_b:
#             part_b = player2.quote.part_b

#         if not part_a or not part_b:
#             return Response({"error": "Match quote not found"}, status=status.HTTP_400_BAD_REQUEST)

#         full_quote = part_a + " " + part_b
#         try:
#             matched_quote = Quote.objects.get(text=full_quote)
#         except Quote.DoesNotExist:
#             return Response({"error": "Combined quote does not match any known quote."}, status=status.HTTP_404_NOT_FOUND)

#         # Check if one of the two players already has a flip number assigned
#         previous_flip = GridFlipLog.objects.filter(player__in=[player1, player2], is_status=True).first()
#         if previous_flip:
#             flip = previous_flip
#         else:
#             # Assign new flip number
#             available_flips = GridFlipLog.objects.filter(is_status=False)
#             if not available_flips.exists():
#                 return Response({"error": "No available flip numbers remaining."}, status=status.HTTP_410_GONE)

#             flip = random.choice(list(available_flips))
#             flip.is_status = True
#             flip.save()

#         # Award group points to both players if not already awarded
#         updated_groups = set()
#         for player in [player1, player2]:
#             if player.group and player.group.id not in updated_groups:
#                 player.group.points += 1
#                 player.group.save()
#                 updated_groups.add(player.group.id)

#         return Response({
#             "flip_number": flip.flip_number,
#             "quote": matched_quote.text,
#             "message": "🎉 Congrats! You've flipped a grid."
#         }, status=status.HTTP_200_OK)

# class VerifyQuotePairView(APIView):
#     def post(self, request):
#         diary_id_1 = request.data.get('diary_id_1')
#         diary_id_2 = request.data.get('diary_id_2')

#         if not diary_id_1 or not diary_id_2:
#             return Response({"error": "Both diary IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             player1 = Player.objects.get(diary_id=diary_id_1)
#             player2 = Player.objects.get(diary_id=diary_id_2)
#         except Player.DoesNotExist:
#             return Response({"error": "One or both diary IDs not found."}, status=status.HTTP_404_NOT_FOUND)

#         # Identify which quote part each player has
#         part_a = part_b = None
#         if player1.quote_part == "A":
#             part_a = player1.quote.part_a
#         elif player1.quote_part == "B":
#             part_b = player1.quote.part_b

#         if player2.quote_part == "A":
#             part_a = player2.quote.part_a if not part_a else part_a
#         elif player2.quote_part == "B":
#             part_b = player2.quote.part_b if not part_b else part_b

#         if not part_a or not part_b:
#             return Response({"error": "Match quote not found"}, status=status.HTTP_400_BAD_REQUEST)
#         print("part_a", part_a)
#         print("part_b", part_b)
#         full_quote = part_a + " " + part_b
#         print("test",full_quote)
#         try:
#             matched_quote = Quote.objects.get(text=full_quote)
#         except Quote.DoesNotExist:
#             return Response({"error": "Match does not found"}, status=status.HTTP_404_NOT_FOUND)

#         available_flips = GridFlipLog.objects.filter(is_status=False)
#         print("available_flips", available_flips)

#         if not available_flips.exists():
#             return Response({"error": "No available flip numbers remaining."}, status=status.HTTP_410_GONE)

#         flip = random.choice(list(available_flips))
#         print("flip", flip)
#         print("flip_number", flip.flip_number)
#         flip.is_status = True
#         flip.save()

#         # Group points increment logic
#         updated_groups = set()
#         for player in [player1, player2]:
#             if player.group and player.group.id not in updated_groups:
#                 group = player.group
#                 group.points += 1
#                 group.save()
#                 updated_groups.add(group.id)

#         return Response({
#             "flip_number": flip.flip_number,
#             "quote": matched_quote.text,
#             "message": "🎉 Congrats! You've flipped a grid."
#         }, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def verifyQuotePairView(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST request required"}, status=405)

#     diary_number = request.data.get("diary_number")
    
#     print(f"Received diary_number: {diary_number}")
#     if not diary_number:
#         return JsonResponse({"error": "Missing diary_number"}, status=400)

#     try:
#         player = Player.objects.get(diary_id=diary_number)
#     except Player.DoesNotExist:
#         return JsonResponse({"error": "Player not found"}, status=404)

#     if player.registered:
#         return JsonResponse({"error": "Player already verified"}, status=400)

#     try:
#         with transaction.atomic():
#             # 1. Update in your main DB
#             player.registered = True
#             player.save()

#             # 2. Update frontend DB using raw SQL
#             with connections['frontend'].cursor() as cursor:
#                 cursor.execute("""
#                     INSERT INTO quote_verifications (diary_number, quote_id, is_verified)
#                     VALUES (%s, %s, TRUE)
#                     ON CONFLICT (diary_number) DO UPDATE
#                     SET quote_id = EXCLUDED.quote_id,
#                         is_verified = TRUE;
#                 """, [player.diary_id, player.quote.id])

#     except Exception as e:
#         return JsonResponse({"error": f"Verification failed: {str(e)}"}, status=500)

#     return JsonResponse({
#         "message": "Quote pair verified successfully.",
#         "diary_number": diary_number,
#         "quote_id": player.quote.id
#     })
    
class GroupPointsView(APIView):
    def get(self, request):
        groups = Group.objects.all().values("name", "points")
        return Response(list(groups), status=status.HTTP_200_OK)