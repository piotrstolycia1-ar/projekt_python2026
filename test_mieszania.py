import pytest
from Projekt_mini_Scada import TankModel

def test_mieszanie_temperatury_50_50():
    # 50 L o 20°C + 50 L o 80°C = 100 L o 50°C
    tank = TankModel("mix", 200.0, 50.0, 20.0)
    tank.add(50.0, 80.0)

    assert tank.volume_l == 100.0
    assert tank.temp_c == pytest.approx(50.0, abs=1e-6)

def test_mieszanie_dolewka_mniejsza():
    # 90 L o 20°C + 10 L o 100°C = 100 L o 28°C
    # T = (90*20 + 10*100)/100 = (1800 + 1000)/100 = 28
    tank = TankModel("mix", 200.0, 90.0, 20.0)
    tank.add(10.0, 100.0)

    assert tank.volume_l == 100.0
    assert tank.temp_c == pytest.approx(28.0, abs=1e-6)

def test_mieszanie_przy_pustym_zbiorniku_ustawia_temperature():
    # jeśli zbiornik był pusty -> temp = Tin
    tank = TankModel("mix", 100.0, 0.0, 0.0)
    tank.add(10.0, 37.0)

    assert tank.volume_l == 10.0
    assert tank.temp_c == pytest.approx(37.0, abs=1e-6)

def test_dolewka_ponad_pojemnosc_nie_przekracza_capacity():
    tank = TankModel("mix", 100.0, 95.0, 20.0)
    added = tank.add(20.0, 80.0)

    assert added == pytest.approx(5.0, abs=1e-6)
    assert tank.volume_l == pytest.approx(100.0, abs=1e-6)

def test_ujemne_i_zero_nie_zmieniaja_stanu():
    tank = TankModel("mix", 100.0, 10.0, 20.0)

    a1 = tank.add(0.0, 80.0)
    a2 = tank.add(-5.0, 80.0)
    r1 = tank.remove(0.0)
    r2 = tank.remove(-3.0)

    assert a1 == 0.0 and a2 == 0.0 and r1 == 0.0 and r2 == 0.0
    assert tank.volume_l == 10.0
    assert tank.temp_c == 20.0

def test_is_empty_i_is_full():
    empty = TankModel("empty", 100.0, 0.0, 20.0)
    full = TankModel("full", 100.0, 100.0, 20.0)

    assert empty.is_empty() is True
    assert empty.is_full() is False

    assert full.is_full() is True
    assert full.is_empty() is False



