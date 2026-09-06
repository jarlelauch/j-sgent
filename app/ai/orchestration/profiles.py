from .capability import ProviderProfile


def build_default_profiles(router):

    profiles = []

    for name, provider in router.providers.items():

        profiles.append(
            ProviderProfile(
                name=name,
                capabilities=set(
                    getattr(
                        provider,
                        "capabilities",
                        {
                            "general",
                        },
                    )
                ),
                max_parallel=getattr(
                    provider,
                    "max_parallel",
                    1,
                ),
            )
        )

    return profiles
