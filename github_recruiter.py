from github import Github
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time

@dataclass
class Developer:
    username: str
    name: str
    bio: str
    location: str
    public_repos: int
    followers: int
    languages: Dict[str, int]
    top_repos: List[dict]
    contributions: int
    score: float
    email: Optional[str] = None

class GithubRecruiter:
    def __init__(self, token: str):
        self.github = Github(token)
        self.rate_limit_delay = 2  # seconds between API calls
    
    def find_developers(self, query: dict) -> List[Developer]:
        """Search for developers based on query parameters"""
        search_query = self._build_query(query)
        developers = []
        
        try:
            users = self.github.search_users(search_query)
            for user in users[:15]:  # Limit to top 15 results
                time.sleep(self.rate_limit_delay)  # Respect rate limits
                dev = self._analyze_developer(user, query)
                if dev and dev.score >= query.get('min_score', 0.5):
                    developers.append(dev)
            
            return sorted(developers, key=lambda x: x.score, reverse=True)
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def _build_query(self, query: dict) -> str:
        """Build GitHub search query string"""
        parts = []
        
        if query.get('languages'):
            parts.extend(f"language:{lang}" for lang in query['languages'])
        
        if query.get('location'):
            parts.append(f"location:{query['location']}")
        
        if query.get('min_followers'):
            parts.append(f"followers:>={query['min_followers']}")
        
        if query.get('min_repos'):
            parts.append(f"repos:>={query['min_repos']}")
            
        return ' '.join(parts)

    def _analyze_developer(self, user, query: dict) -> Optional[Developer]:
        """Analyze a developer's profile and calculate score"""
        try:
            profile = user.get_user()
            time.sleep(self.rate_limit_delay)
            
            # Get top repositories
            repos = list(profile.get_repos(sort='stars', direction='desc'))[:5]
            languages = self._get_languages(repos)
            top_repos = self._get_top_repos(repos)
            contributions = self._get_contributions(profile)
            
            score = self._calculate_score(
                profile=profile,
                languages=languages,
                contributions=contributions,
                criteria=query
            )
            
            return Developer(
                username=profile.login,
                name=profile.name or profile.login,
                bio=profile.bio or "",
                location=profile.location or "",
                public_repos=profile.public_repos,
                followers=profile.followers,
                languages=languages,
                top_repos=top_repos,
                contributions=contributions,
                score=score,
                email=profile.email
            )
            
        except Exception as e:
            print(f"Error analyzing {user.login}: {e}")
            return None

    def _get_languages(self, repos) -> Dict[str, int]:
        """Get language statistics from repositories"""
        languages = {}
        for repo in repos:
            try:
                for lang, bytes_count in repo.get_languages().items():
                    languages[lang] = languages.get(lang, 0) + bytes_count
                time.sleep(self.rate_limit_delay)
            except:
                continue
        return languages

    def _get_top_repos(self, repos) -> List[dict]:
        """Get developer's top repositories"""
        top_repos = []
        for repo in repos:
            if not repo.fork:  # Skip forks
                top_repos.append({
                    'name': repo.name,
                    'stars': repo.stargazers_count,
                    'description': repo.description,
                    'url': repo.html_url
                })
        return top_repos

    def _get_contributions(self, user) -> int:
        """Calculate user's contributions in the last year"""
        try:
            events = user.get_events()
            count = 0
            one_year_ago = datetime.now() - timedelta(days=365)
            
            for event in events:
                if event.created_at < one_year_ago:
                    break
                if event.type in ['PushEvent', 'PullRequestEvent', 'IssuesEvent']:
                    count += 1
            return count
        except:
            return 0

    def _calculate_score(self, profile, languages: dict, contributions: int, criteria: dict) -> float:
        """Calculate developer's match score based on criteria"""
        score = 0.0
        weights = {
            'languages': 0.3,
            'repos': 0.2,
            'followers': 0.15,
            'contributions': 0.25,
            'location': 0.1
        }
        
        # Language match
        if criteria.get('languages'):
            matching_langs = set(criteria['languages']).intersection(languages.keys())
            score += weights['languages'] * (len(matching_langs) / len(criteria['languages']))
        
        # Repository count
        if profile.public_repos >= criteria.get('min_repos', 5):
            score += weights['repos']
        
        # Followers
        if profile.followers >= criteria.get('min_followers', 50):
            score += weights['followers']
        
        # Contributions
        if contributions >= criteria.get('min_contributions', 100):
            score += weights['contributions']
        
        # Location match
        if criteria.get('location') and profile.location:
            if criteria['location'].lower() in profile.location.lower():
                score += weights['location']
        
        return min(score, 1.0) 