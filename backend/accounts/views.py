from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializers import RegisterSerializer, PortfolioSerializer
from .models import Portfolio


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Registration successful"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
        })


class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    # Create Portfolio
    def post(self, request):
        if Portfolio.objects.filter(user=request.user).exists():
            return Response(
                {"error": "Portfolio already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PortfolioSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get Portfolio
    def get(self, request):
        portfolio = Portfolio.objects.filter(user=request.user).first()

        if portfolio is None:
            return Response(
                {"error": "Portfolio not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)

    # Update Portfolio
    def put(self, request):
        portfolio = Portfolio.objects.filter(user=request.user).first()

        if portfolio is None:
            return Response(
                {"error": "Portfolio not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PortfolioSerializer(
            portfolio,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # Delete Portfolio
    def delete(self, request):
        portfolio = Portfolio.objects.filter(user=request.user).first()

        if portfolio is None:
            return Response(
                {"error": "Portfolio not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        portfolio.delete()

        return Response(
            {"message": "Portfolio deleted successfully"},
            status=status.HTTP_200_OK
        )