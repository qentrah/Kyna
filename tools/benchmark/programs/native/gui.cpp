// Owns the fixed Qt timer-event delivery C++ performance oracle.
#include <QGuiApplication>
#include <QTimer>
#include <iostream>
int main(int argc, char **argv) {
  QGuiApplication application(argc, argv);
  int count = 0;
  for (int index = 0; index < 1000; ++index)
    QTimer::singleShot(0, &application, [&] { if (++count == 1000) application.quit(); });
  QTimer::singleShot(10000, &application, &QGuiApplication::quit);
  application.exec();
  if (count != 1000) return 1;
  std::cout << count << '\n';
}
