class ChatMessage {
  final String id;
  final String sender;
  final String content;
  final bool isRead;
  final String createdAt;

  const ChatMessage({
    required this.id,
    required this.sender,
    required this.content,
    this.isRead = false,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      sender: json['sender'] as String,
      content: json['content'] as String,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: json['created_at'] as String,
    );
  }
}
