class User {
  final String id;
  final String email;
  final String name;
  final String? dateOfBirth;
  final String? avatarId;
  final String? nativeLanguageId;
  final bool isActive;
  final bool isBanned;

  const User({
    required this.id,
    required this.email,
    required this.name,
    this.dateOfBirth,
    this.avatarId,
    this.nativeLanguageId,
    this.isActive = true,
    this.isBanned = false,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      email: json['email'] as String,
      name: json['name'] as String,
      dateOfBirth: json['date_of_birth'] as String?,
      avatarId: json['avatar_id'] as String?,
      nativeLanguageId: json['native_language_id'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      isBanned: json['is_banned'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'date_of_birth': dateOfBirth,
      'avatar_id': avatarId,
      'native_language_id': nativeLanguageId,
      'is_active': isActive,
      'is_banned': isBanned,
    };
  }
}
